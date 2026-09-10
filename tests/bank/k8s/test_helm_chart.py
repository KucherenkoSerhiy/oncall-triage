"""`helm template` golden test for the nordwind-bank chart.

Skipped when `helm` isn't on PATH; the `helm` CI job installs it.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
CHART_DIR = REPO_ROOT / "deploy" / "helm" / "nordwind-bank"

EXPECTED_RULES = {
    "CardsAuthHighLatency": "cards-authorization",
    "CardsAuthErrorRatio": "cards-authorization",
    "FraudScoreDrift": "fraud-scoring",
    "FraudScoringCrashLoop": "fraud-scoring",
    "OpenBankingRateLimitStorm": "open-banking-api",
    "OpenBankingCertExpiringSoon": "open-banking-api",
    "KafkaBrokerDown": "kafka",
    "KafkaRelayLag": "kafka-relay",
    "AlertsBridgeDown": "alerts-bridge",
    "KafkaRelayDown": "kafka-relay",
}
# KafkaConsumerLag carries a dynamic `service` (the consumergroup label, via
# label_replace) rather than a static one - checked separately below.
_DYNAMIC_SERVICE_RULE = "KafkaConsumerLag"

pytestmark = pytest.mark.skipif(shutil.which("helm") is None, reason="helm is not on PATH")


def _render(*extra_args: str) -> list[dict]:
    # Release name "nordwind-bank" matches Taskfile.yml's `estate-up` (the
    # only place this chart is actually installed) - the alerts-bridge
    # Service name is release-prefixed and needs to match the real thing.
    output = subprocess.run(  # noqa: S603 - fixed argv, no shell, no untrusted input
        ["helm", "template", "nordwind-bank", str(CHART_DIR), *extra_args],  # noqa: S607 - helm is expected on PATH
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [doc for doc in yaml.safe_load_all(output) if doc]


def test_prometheus_rule_has_the_expected_rules_with_service_labels():
    docs = _render()
    rule_doc = next(doc for doc in docs if doc["kind"] == "PrometheusRule")
    group = next(g for g in rule_doc["spec"]["groups"] if g["name"] == "nordwind-bank.rules")
    rules = {rule["alert"]: rule for rule in group["rules"]}

    assert set(rules) == set(EXPECTED_RULES) | {_DYNAMIC_SERVICE_RULE}
    for name, service in EXPECTED_RULES.items():
        assert rules[name]["labels"]["service"] == service
        assert "severity" in rules[name]["labels"]
        assert "summary" in rules[name]["annotations"]
        assert "description" in rules[name]["annotations"]

    dynamic_rule = rules[_DYNAMIC_SERVICE_RULE]
    assert "service" not in dynamic_rule["labels"]
    assert "severity" in dynamic_rule["labels"]
    assert "summary" in dynamic_rule["annotations"]
    assert "description" in dynamic_rule["annotations"]


def test_prometheus_rule_kafka_only_rules_absent_when_kafka_disabled():
    docs = _render("--set", "kafka.enabled=false")
    rule_doc = next(doc for doc in docs if doc["kind"] == "PrometheusRule")
    group = next(g for g in rule_doc["spec"]["groups"] if g["name"] == "nordwind-bank.rules")
    rules = {rule["alert"] for rule in group["rules"]}

    assert rules == {
        "CardsAuthHighLatency",
        "CardsAuthErrorRatio",
        "FraudScoreDrift",
        "FraudScoringCrashLoop",
        "OpenBankingRateLimitStorm",
        "OpenBankingCertExpiringSoon",
    }


def test_every_deployment_is_read_only_root_filesystem():
    docs = _render()
    deployments = [doc for doc in docs if doc["kind"] == "Deployment"]
    assert len(deployments) == 5

    for deployment in deployments:
        for container in deployment["spec"]["template"]["spec"]["containers"]:
            assert container["securityContext"]["readOnlyRootFilesystem"] is True


def test_alerts_bridge_and_kafka_relay_absent_when_kafka_disabled():
    docs = _render("--set", "kafka.enabled=false")
    deployment_names = {doc["metadata"]["name"] for doc in docs if doc["kind"] == "Deployment"}

    assert deployment_names == {"cards-authorization", "fraud-scoring", "open-banking-api"}


def test_alerts_bridge_service_name_is_release_prefixed():
    docs = _render()
    services = {doc["metadata"]["name"] for doc in docs if doc["kind"] == "Service"}

    assert "nordwind-bank-alerts-bridge" in services
