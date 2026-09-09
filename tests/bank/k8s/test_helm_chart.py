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
}

pytestmark = pytest.mark.skipif(shutil.which("helm") is None, reason="helm is not on PATH")


def _render() -> list[dict]:
    output = subprocess.run(  # noqa: S603 - fixed argv, no shell, no untrusted input
        ["helm", "template", str(CHART_DIR)],  # noqa: S607 - helm is expected on PATH
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [doc for doc in yaml.safe_load_all(output) if doc]


def test_prometheus_rule_has_the_six_rules_with_service_labels():
    docs = _render()
    rule_doc = next(doc for doc in docs if doc["kind"] == "PrometheusRule")
    group = next(g for g in rule_doc["spec"]["groups"] if g["name"] == "nordwind-bank.rules")
    rules = {rule["alert"]: rule for rule in group["rules"]}

    assert set(rules) == set(EXPECTED_RULES)
    for name, service in EXPECTED_RULES.items():
        assert rules[name]["labels"]["service"] == service
        assert "severity" in rules[name]["labels"]
        assert "summary" in rules[name]["annotations"]
        assert "description" in rules[name]["annotations"]


def test_every_deployment_is_read_only_root_filesystem():
    docs = _render()
    deployments = [doc for doc in docs if doc["kind"] == "Deployment"]
    assert len(deployments) == 3

    for deployment in deployments:
        for container in deployment["spec"]["template"]["spec"]["containers"]:
            assert container["securityContext"]["readOnlyRootFilesystem"] is True
