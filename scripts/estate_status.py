"""Print Kubernetes bank estate status (stdlib only, like scripts/smoke.py).

Pods in `bank` and `monitoring`, the `nordwind-faults` ConfigMap contents,
and firing alerts from the Alertmanager API. `--kafka` (M7a) additionally
prints `KafkaTopic`s and per-group consumer lag, read from inside the
broker pod with the `admin` `KafkaUser`'s SCRAM credentials (superuser -
declared only so this command can run `kafka-consumer-groups.sh --describe`
across every group; no other client uses it). Run by `task estate-status`
against a live kind cluster (`task estate-up`).
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

_DEFAULT_ALERTMANAGER = "http://localhost:9093"
_HTTP_TIMEOUT_SECONDS = 10
# The Taskfile always installs the chart as release "nordwind-bank" (see
# `task estate-up`), which is also the Strimzi Kafka cluster's name (the
# chart's Kafka resource is named `{{ .Release.Name }}` - see
# deploy/helm/nordwind-bank/templates/kafka/kafka.yaml) - so the generated
# cluster CA Secret name and the broker pod's mounted truststore path below
# are fixed rather than discovered.
_KAFKA_CLUSTER_NAME = "nordwind-bank"
_BROKER_POD_LABEL_SELECTOR = "strimzi.io/pool-name=broker"
_ADMIN_CLIENT_CONFIG = (
    "security.protocol=SASL_SSL\n"
    "sasl.mechanism=SCRAM-SHA-512\n"
    "sasl.jaas.config=org.apache.kafka.common.security.scram.ScramLoginModule required "
    'username="admin" password="{password}";\n'
    "ssl.truststore.location=/opt/kafka/cluster-ca-certs/ca.p12\n"
    "ssl.truststore.password={truststore_password}\n"
    "ssl.truststore.type=PKCS12\n"
    # The broker's certificate SAN doesn't cover "localhost" (the address
    # used from inside the broker pod itself), so hostname verification
    # must be switched off - otherwise the TLS handshake fails outright.
    "ssl.endpoint.identification.algorithm=\n"
)


def kubectl(*args: str, run=subprocess.run) -> str:
    result = run(
        ["kubectl", *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def http(method: str, url: str) -> tuple[int, bytes]:
    request = urllib.request.Request(url, method=method)  # noqa: S310 - fixed local Alertmanager URL
    try:
        with urllib.request.urlopen(request, timeout=_HTTP_TIMEOUT_SECONDS) as response:  # noqa: S310
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def print_pods(namespace: str, out=sys.stdout) -> None:
    print(f"--- pods: {namespace} ---", file=out)
    print(kubectl("-n", namespace, "get", "pods").rstrip("\n"), file=out)


def print_faults(out=sys.stdout) -> None:
    print("--- faults (nordwind-faults ConfigMap) ---", file=out)
    raw = kubectl("-n", "bank", "get", "configmap", "nordwind-faults", "-o", "json")
    data = json.loads(raw).get("data", {})
    for service, mode in sorted(data.items()):
        print(f"{service:<20}{mode or '(normal)'}", file=out)


def print_firing_alerts(alertmanager: str, out=sys.stdout) -> None:
    print("--- firing alerts (Alertmanager) ---", file=out)
    status, body = http("GET", f"{alertmanager}/api/v2/alerts?active=true")
    if status != 200:
        print(f"error: HTTP {status} from Alertmanager", file=out)
        return

    alerts = json.loads(body)
    if not alerts:
        print("(none firing)", file=out)
        return

    print(f"{'NAME':<28}{'SERVICE':<20}{'SEVERITY':<10}STARTED", file=out)
    for alert in alerts:
        labels = alert.get("labels", {})
        print(
            f"{labels.get('alertname', '?'):<28}{labels.get('service', '?'):<20}"
            f"{labels.get('severity', '?'):<10}{alert.get('startsAt', '?')}",
            file=out,
        )


def print_kafka_topics(out=sys.stdout) -> None:
    print("--- kafka topics ---", file=out)
    print(kubectl("-n", "bank", "get", "kafkatopics").rstrip("\n"), file=out)


def _secret_value(name: str, key: str, run=subprocess.run) -> str:
    raw = kubectl("-n", "bank", "get", "secret", name, "-o", f"jsonpath={{.data.{key}}}", run=run)
    return base64.b64decode(raw).decode()


def _broker_pod_name(run=subprocess.run) -> str:
    return kubectl(
        "-n",
        "bank",
        "get",
        "pod",
        "-l",
        _BROKER_POD_LABEL_SELECTOR,
        "-o",
        "jsonpath={.items[0].metadata.name}",
        run=run,
    ).strip()


def print_kafka_consumer_lag(out=sys.stdout, run=subprocess.run) -> None:
    print("--- kafka consumer-group lag ---", file=out)
    pod = _broker_pod_name(run=run)
    password = _secret_value("admin", "password", run=run)
    truststore_password = _secret_value(
        f"{_KAFKA_CLUSTER_NAME}-cluster-ca-cert", "ca.password", run=run
    )
    config = _ADMIN_CLIENT_CONFIG.format(password=password, truststore_password=truststore_password)
    script = (
        f"cat > /tmp/admin.properties <<'EOF'\n{config}EOF\n"
        "bin/kafka-consumer-groups.sh --bootstrap-server localhost:9093 "
        "--command-config /tmp/admin.properties --describe --all-groups"
    )
    output = kubectl("-n", "bank", "exec", pod, "--", "sh", "-c", script, run=run)
    print(output.rstrip("\n") or "(no consumer groups)", file=out)


def print_forwarder_hint(out=sys.stdout) -> None:
    if not os.environ.get("FORWARDER_URL"):
        print("--- forwarder ---", file=out)
        print(
            "FORWARDER_URL is not set: route B goes to the dummy receiver "
            "(http://127.0.0.1:9/) - alerts fire but never leave the cluster.",
            file=out,
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--alertmanager",
        default=os.environ.get("ALERTMANAGER_URL", _DEFAULT_ALERTMANAGER),
    )
    parser.add_argument(
        "--kafka", action="store_true", help="also print KafkaTopics and consumer-group lag"
    )
    args = parser.parse_args(argv)

    print_pods("bank")
    print_pods("monitoring")
    print_faults()
    print_firing_alerts(args.alertmanager)
    if args.kafka:
        print_kafka_topics()
        print_kafka_consumer_lag()
    print_forwarder_hint()
    return 0


if __name__ == "__main__":
    sys.exit(main())
