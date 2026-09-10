"""Contract tests for route A end to end: `alerts-bridge` produces to a real
Redpanda broker, `kafka-relay` consumes it and POSTs to a local HTTP stub -
not fakes, see `tests/bank/k8s/test_alerts_bridge.py` /
`test_kafka_relay.py` for the fake-producer/fake-http unit tests of the same
service code.
"""

from __future__ import annotations

import json
import threading
import time
import uuid
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import ClassVar

import confluent_kafka
import pytest
from prometheus_client import CollectorRegistry
from testcontainers.community.kafka import RedpandaContainer

from bank.k8s._shared.kafka import ConsumerLoop, KafkaPublisher
from bank.k8s.alerts_bridge.service import ALERTS_RAW_TOPIC, AlertsBridgeService
from bank.k8s.kafka_relay.service import KafkaRelayService
from services.ingest import hmac_auth
from tests.contract.conftest import _REDPANDA_IMAGE, docker_available

pytestmark = [
    pytest.mark.contract,
    pytest.mark.skipif(not docker_available(), reason="Docker is not available"),
]

_SECRET = b"contract-test-secret"
_DRAIN_TIMEOUT_SECONDS = 30.0
_ADDRESS_FAMILY = {"broker.address.family": "v4"}


@pytest.fixture
def bootstrap() -> Iterator[str]:
    # Function-scoped, not the module-scoped `bootstrap` in conftest.py:
    # both tests here produce to the fixed `alerts.raw` topic name (the
    # services hardcode it), and kafka-relay POSTs *every* message it
    # consumes - a leftover message from an earlier test sharing one broker
    # would land on this test's stub and change which response it gets.
    with RedpandaContainer(_REDPANDA_IMAGE) as redpanda:
        yield redpanda.get_bootstrap_server().replace("localhost", "127.0.0.1")


class _Stub(BaseHTTPRequestHandler):
    """Records every POST, verifies its HMAC, and answers with the next
    status code from the class-level queue (defaults to 200)."""

    responses: ClassVar[list[int]] = []
    requests: ClassVar[list[dict]] = []
    lock = threading.Lock()

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        try:
            hmac_auth.verify(
                _SECRET,
                self.headers["X-Nordwind-Timestamp"],
                body,
                self.headers["X-Nordwind-Signature"],
            )
            verified = True
        except hmac_auth.HmacError:
            verified = False

        with self.lock:
            status = self.responses.pop(0) if self.responses else 200
            self.requests.append({"body": json.loads(body), "verified": verified})

        self.send_response(status)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:
        pass


@pytest.fixture
def stub() -> Iterator[tuple[str, type[_Stub]]]:
    _Stub.responses = []
    _Stub.requests = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Stub)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/alerts", _Stub
    finally:
        server.shutdown()
        thread.join()


def _wait_until(predicate, timeout: float = _DRAIN_TIMEOUT_SECONDS) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.2)
    raise AssertionError(f"condition not met within {timeout}s")


def test_bridge_produces_and_relay_consumes_and_posts_with_a_verifiable_hmac(bootstrap, stub):
    ingest_url, stub_cls = stub
    fingerprint = str(uuid.uuid4())
    alert = {
        "fingerprint": fingerprint,
        "status": "firing",
        "labels": {"alertname": "KafkaConsumerLag", "service": "fraud-scoring"},
        "annotations": {"summary": "lag"},
        "startsAt": "2026-01-01T00:00:00Z",
    }

    bridge_registry = CollectorRegistry()
    producer = KafkaPublisher(
        confluent_kafka.Producer({"bootstrap.servers": bootstrap, **_ADDRESS_FAMILY})
    )
    bridge = AlertsBridgeService(bridge_registry, producer)
    status = bridge.handle_webhook(
        {"receiver": "route-a-kafka", "status": "firing", "alerts": [alert]}
    )
    assert status == 202

    relay_registry = CollectorRegistry()
    relay = KafkaRelayService(relay_registry, ingest_url, _SECRET)
    consumer = confluent_kafka.Consumer(
        {
            "bootstrap.servers": bootstrap,
            "group.id": f"kafka-relay-{uuid.uuid4()}",
            "enable.auto.commit": False,
            "auto.offset.reset": "earliest",
            **_ADDRESS_FAMILY,
        }
    )
    consumer.subscribe([ALERTS_RAW_TOPIC])
    loop = ConsumerLoop(consumer, relay.handle_message)
    loop.start()
    try:
        _wait_until(
            lambda: any(
                r["body"]["payload"]["alerts"][0]["fingerprint"] == fingerprint
                for r in stub_cls.requests
            )
        )
    finally:
        loop.stop()
        consumer.close()

    matching = [
        r
        for r in stub_cls.requests
        if r["body"]["payload"]["alerts"][0]["fingerprint"] == fingerprint
    ]
    assert len(matching) == 1
    request = matching[0]
    assert request["verified"] is True
    assert request["body"]["source"] == "alertmanager"
    assert request["body"]["payload"]["receiver"] == "route-a-kafka"
    assert request["body"]["payload"]["status"] == "firing"
    assert request["body"]["payload"]["alerts"][0]["labels"]["alertname"] == "KafkaConsumerLag"
    assert relay_registry.get_sample_value("relay_posted_total") == 1


def test_relay_retries_a_failing_stub_then_commits_after_a_2xx(bootstrap, stub):
    ingest_url, stub_cls = stub
    stub_cls.responses = [500]  # first attempt fails, second (retry) succeeds
    fingerprint = str(uuid.uuid4())
    alert = {
        "fingerprint": fingerprint,
        "status": "firing",
        "labels": {"alertname": "KafkaBrokerDown", "service": "kafka"},
        "annotations": {},
        "startsAt": "2026-01-01T00:00:00Z",
    }

    bridge_registry = CollectorRegistry()
    producer = KafkaPublisher(
        confluent_kafka.Producer({"bootstrap.servers": bootstrap, **_ADDRESS_FAMILY})
    )
    bridge = AlertsBridgeService(bridge_registry, producer)
    bridge.handle_webhook({"receiver": "route-a-kafka", "status": "firing", "alerts": [alert]})

    relay_registry = CollectorRegistry()
    relay = KafkaRelayService(
        relay_registry, ingest_url, _SECRET, sleep=lambda _seconds: None, backoff=(0.0,)
    )
    consumer = confluent_kafka.Consumer(
        {
            "bootstrap.servers": bootstrap,
            "group.id": f"kafka-relay-{uuid.uuid4()}",
            "enable.auto.commit": False,
            "auto.offset.reset": "earliest",
            **_ADDRESS_FAMILY,
        }
    )
    consumer.subscribe([ALERTS_RAW_TOPIC])
    loop = ConsumerLoop(consumer, relay.handle_message)
    loop.start()
    try:
        # Wait for the retry to actually succeed (not just for the first,
        # failing attempt to land) before inspecting the stub's request log.
        _wait_until(lambda: (relay_registry.get_sample_value("relay_posted_total") or 0) >= 1)
    finally:
        loop.stop()
        consumer.close()

    matching = [
        r
        for r in stub_cls.requests
        if r["body"]["payload"]["alerts"][0]["fingerprint"] == fingerprint
    ]
    assert len(matching) == 2, "expected exactly one retry (500 then 200)"
    assert all(r["verified"] for r in matching)
    assert relay_registry.get_sample_value("relay_posted_total") == 1
    assert relay_registry.get_sample_value("relay_failures_total") == 1
    assert relay_registry.get_sample_value("relay_dropped_total") == 0
