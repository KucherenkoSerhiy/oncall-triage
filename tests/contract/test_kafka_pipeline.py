"""Contract tests: the real `confluent_kafka` wiring against a real broker
(Redpanda via testcontainers), not fakes - see `tests/bank/k8s/` for the
fake-`Publisher`/fake-consumer unit tests of the same service code.

Each test builds its own consumer group(s) so leftover messages from an
earlier test in this module (sharing one Redpanda container) can't change
an assertion; `_drain_until` filters by a marker unique to the test rather
than assuming an exact message count.
"""

from __future__ import annotations

import json
import time
import uuid

import confluent_kafka
import confluent_kafka.admin
import pytest
from prometheus_client import CollectorRegistry

from bank.k8s._shared.faults import FaultFile
from bank.k8s._shared.kafka import ConsumerLoop, KafkaPublisher
from bank.k8s.cards_authorization.service import CardsAuthorizationService
from bank.k8s.fraud_scoring.service import FraudScoringService
from bank.k8s.open_banking_api.service import OpenBankingApiService
from tests.contract.conftest import docker_available

pytestmark = [
    pytest.mark.contract,
    pytest.mark.skipif(not docker_available(), reason="Docker is not available"),
]

_DRAIN_TIMEOUT_SECONDS = 30.0
# Force IPv4: some Docker hosts resolve the broker's advertised hostname to
# the IPv6 loopback first, and librdkafka pays a slow (~20s) connect timeout
# on that address, per client, before falling back to IPv4.
_ADDRESS_FAMILY = {"broker.address.family": "v4"}


def _producer(bootstrap: str) -> confluent_kafka.Producer:
    return confluent_kafka.Producer({"bootstrap.servers": bootstrap, **_ADDRESS_FAMILY})


def _consumer(bootstrap: str, group: str, topics: list[str]) -> confluent_kafka.Consumer:
    consumer = confluent_kafka.Consumer(
        {
            "bootstrap.servers": bootstrap,
            "group.id": group,
            "enable.auto.commit": False,
            "auto.offset.reset": "earliest",
            **_ADDRESS_FAMILY,
        }
    )
    consumer.subscribe(topics)
    return consumer


def _drain_until(consumer, predicate, timeout: float = _DRAIN_TIMEOUT_SECONDS) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        msg = consumer.poll(1.0)
        if msg is None or msg.error():
            continue
        event = json.loads(msg.value())
        consumer.commit(msg)
        if predicate(event):
            return event
    raise AssertionError(f"no matching message within {timeout}s")


def _fault_file(tmp_path, valid_modes) -> FaultFile:
    return FaultFile(path=str(tmp_path / "fault"), ttl=0.01, valid_modes=valid_modes)


def test_cards_authorization_publishes_a_real_card_authorized_event(bootstrap, tmp_path):
    registry = CollectorRegistry()
    publisher = KafkaPublisher(_producer(bootstrap))
    fault_file = _fault_file(tmp_path, ("timeouts", "issuer-down"))
    service = CardsAuthorizationService(registry, fault_file=fault_file, publisher=publisher)

    result = service.work()

    consumer = _consumer(bootstrap, f"verify-cards-{uuid.uuid4()}", ["card.authorized"])
    try:
        event = _drain_until(consumer, lambda e: e["result"] == result["result"])
    finally:
        consumer.close()

    assert set(event) == {"txn_id", "amount", "currency", "result", "ts"}
    assert event["currency"] == "EUR"


def test_fraud_scoring_consumes_card_authorized_and_produces_fraud_scored(bootstrap, tmp_path):
    txn_id = str(uuid.uuid4())
    producer = _producer(bootstrap)
    producer.produce(
        "card.authorized",
        key=txn_id,
        value=json.dumps(
            {"txn_id": txn_id, "amount": 42.0, "currency": "EUR", "result": "ok", "ts": time.time()}
        ).encode(),
    )
    producer.flush(10)

    registry = CollectorRegistry()
    fault_file = _fault_file(tmp_path, ("model-drift", "latency", "crashloop", "lag"))
    fraud_publisher = KafkaPublisher(_producer(bootstrap))
    service = FraudScoringService(registry, fault_file=fault_file, publisher=fraud_publisher)

    card_consumer = _consumer(bootstrap, f"fraud-scoring-{uuid.uuid4()}", ["card.authorized"])
    loop = ConsumerLoop(card_consumer, service.handle_card_authorized, fault_file=fault_file)
    loop.start()
    try:
        result_consumer = _consumer(bootstrap, f"verify-fraud-{uuid.uuid4()}", ["fraud.scored"])
        try:
            event = _drain_until(result_consumer, lambda e: e["txn_id"] == txn_id)
        finally:
            result_consumer.close()
    finally:
        loop.stop()
        card_consumer.close()

    assert 0.0 <= event["score"] <= 1.0


def test_open_banking_api_consumes_fraud_scored(bootstrap):
    txn_id = str(uuid.uuid4())
    producer = _producer(bootstrap)
    producer.produce(
        "fraud.scored",
        key=txn_id,
        value=json.dumps({"txn_id": txn_id, "score": 0.1, "ts": time.time()}).encode(),
    )
    producer.flush(10)

    registry = CollectorRegistry()
    service = OpenBankingApiService(registry)

    # A fresh (earliest-offset) group on a topic this module's other tests
    # also publish to may see more than just this test's own message - the
    # counter increments once per message regardless, so assert >= 1 rather
    # than pinning an exact count shared module-scoped topic state can't
    # guarantee.
    consumer = _consumer(bootstrap, f"open-banking-api-{uuid.uuid4()}", ["fraud.scored"])
    loop = ConsumerLoop(consumer, service.handle_fraud_scored)
    loop.start()
    try:
        deadline = time.monotonic() + _DRAIN_TIMEOUT_SECONDS
        while (
            registry.get_sample_value("openbanking_events_consumed_total") or 0
        ) < 1 and time.monotonic() < deadline:
            time.sleep(0.5)
    finally:
        loop.stop()
        consumer.close()

    assert (registry.get_sample_value("openbanking_events_consumed_total") or 0) >= 1


def test_lag_fault_stops_consumption_and_group_lag_grows(bootstrap, tmp_path):
    fault_path = tmp_path / "fault"
    fault_path.write_text("")
    fault_file = FaultFile(path=str(fault_path), ttl=0.01, valid_modes=("lag",))
    group = f"lag-test-{uuid.uuid4()}"

    registry = CollectorRegistry()
    service = FraudScoringService(registry, fault_file=fault_file)
    consumer = _consumer(bootstrap, group, ["card.authorized"])
    loop = ConsumerLoop(
        consumer, service.handle_card_authorized, fault_file=fault_file, pause_mode="lag"
    )
    loop.start()
    try:
        # Catch the group up to the current end of the topic before pausing,
        # so the lag measured below is caused only by what's produced next.
        deadline = time.monotonic() + _DRAIN_TIMEOUT_SECONDS
        while _group_lag(bootstrap, group, "card.authorized") != 0 and time.monotonic() < deadline:
            time.sleep(0.5)
        assert _group_lag(bootstrap, group, "card.authorized") == 0

        fault_path.write_text("lag")
        # The loop's poll_timeout defaults to 1.0s and it may already be
        # blocked inside consumer.poll(1.0) when the fault flips, so wait
        # comfortably past that before producing.
        time.sleep(1.5)

        producer = _producer(bootstrap)
        for _ in range(5):
            producer.produce(
                "card.authorized", value=json.dumps({"txn_id": str(uuid.uuid4())}).encode()
            )
        producer.flush(10)

        deadline = time.monotonic() + _DRAIN_TIMEOUT_SECONDS
        lag = 0
        while time.monotonic() < deadline:
            lag = _group_lag(bootstrap, group, "card.authorized")
            if lag > 0:
                break
            time.sleep(0.5)
        assert lag >= 5

        fault_path.write_text("")
        deadline = time.monotonic() + _DRAIN_TIMEOUT_SECONDS
        while _group_lag(bootstrap, group, "card.authorized") != 0 and time.monotonic() < deadline:
            time.sleep(0.5)
        assert _group_lag(bootstrap, group, "card.authorized") == 0
    finally:
        loop.stop()
        consumer.close()


def _group_lag(bootstrap: str, group: str, topic: str, partition: int = 0) -> int:
    watermark_consumer = confluent_kafka.Consumer(
        {"bootstrap.servers": bootstrap, "group.id": f"watermark-{uuid.uuid4()}", **_ADDRESS_FAMILY}
    )
    try:
        tp = confluent_kafka.TopicPartition(topic, partition)
        _, high = watermark_consumer.get_watermark_offsets(tp, timeout=10, cached=False)
    finally:
        watermark_consumer.close()

    admin = confluent_kafka.admin.AdminClient({"bootstrap.servers": bootstrap, **_ADDRESS_FAMILY})
    group_futures = admin.list_consumer_group_offsets(
        [confluent_kafka.ConsumerGroupTopicPartitions(group)]
    )
    result = group_futures[group].result(timeout=10)
    committed = 0
    for committed_tp in result.topic_partitions:
        if (
            committed_tp.topic == topic
            and committed_tp.partition == partition
            and committed_tp.offset >= 0
        ):
            committed = committed_tp.offset
    return max(0, high - committed)
