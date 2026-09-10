"""M8: scripts/c4_drift.py.

A deliberate-failure test over a temp repo layout, plus the happy path
over the real repository (skipped if `helm` isn't on PATH - without it
the Kubernetes estate's containers can't be confirmed at all, see
scripts/c4_drift.py's module docstring).
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from scripts import c4_drift

REPO_ROOT = Path(__file__).resolve().parents[1]

_DSL = """\
workspace "Test" "A tiny model for the deliberate-failure test." {
    model {
        sys = softwareSystem "Test System" "..." {
            tagged = container "Tagged" "Has a matching Terraform tag." "Tech" "Deployable"
            untagged = container "Untagged" "Has no resource anywhere." "Tech" "Deployable"
            notDeployable = container "Not deployable" "Conceptual only, no tag expected." "Tech"
        }
    }
    views {
    }
}
"""

_MAIN_TF = """\
resource "aws_s3_bucket" "tagged" {
  bucket = "tagged-bucket"
  tags = {
    c4_container = "tagged"
  }
}

resource "aws_s3_bucket" "untagged_resource" {
  bucket = "untagged-bucket"
}

resource "aws_s3_bucket" "stray" {
  bucket = "stray-bucket"
  tags = {
    c4_container = "not_in_model"
  }
}
"""


def _write_temp_repo(tmp_path: Path) -> Path:
    (tmp_path / "docs" / "c4").mkdir(parents=True)
    (tmp_path / "docs" / "c4" / "workspace.dsl").write_text(_DSL, encoding="utf-8")
    (tmp_path / "infra" / "fakeroot").mkdir(parents=True)
    (tmp_path / "infra" / "fakeroot" / "main.tf").write_text(_MAIN_TF, encoding="utf-8")
    return tmp_path


def test_deliberate_failure_reports_both_rows_and_exits_1(tmp_path: Path, capsys):
    repo = _write_temp_repo(tmp_path)

    exit_code = c4_drift.main(["--repo-root", str(repo)])

    report = capsys.readouterr().out
    assert exit_code == 1
    assert "| untagged | yes | no | skipped | - |" in report
    assert "not_in_model" in report
    assert "| tagged | yes | yes |" in report
    assert "notDeployable" in report


def test_allow_listed_container_does_not_fail(tmp_path: Path, capsys):
    repo = _write_temp_repo(tmp_path)
    (repo / "docs" / "c4" / "drift-allow.yaml").write_text(
        "- container: untagged\n  reason: deliberately untagged for this test\n"
        "- container: not_in_model\n  reason: deliberately stray for this test\n",
        encoding="utf-8",
    )

    exit_code = c4_drift.main(["--repo-root", str(repo)])

    report = capsys.readouterr().out
    assert exit_code == 0
    assert "allow-listed: deliberately untagged" in report
    assert "allow-listed: deliberately stray" in report


def test_strict_fails_when_helm_is_skipped_even_without_other_violations(tmp_path: Path, capsys):
    repo = _write_temp_repo(tmp_path)
    (repo / "docs" / "c4" / "drift-allow.yaml").write_text(
        "- container: untagged\n  reason: deliberately untagged for this test\n"
        "- container: not_in_model\n  reason: deliberately stray for this test\n",
        encoding="utf-8",
    )

    assert c4_drift.main(["--repo-root", str(repo)]) == 0
    assert c4_drift.main(["--repo-root", str(repo), "--strict"]) == 1


def test_parse_terraform_reports_provider_default_tags_as_root_default(tmp_path: Path):
    root = tmp_path / "infra" / "aws"
    root.mkdir(parents=True)
    (root / "main.tf").write_text(
        'provider "aws" {\n'
        "  default_tags {\n"
        "    tags = {\n"
        '      c4_container = "x"\n'
        "    }\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )

    tags = c4_drift.parse_terraform(tmp_path / "infra")

    assert len(tags) == 1
    assert tags[0].container == "x"
    assert tags[0].root_default is True
    assert "root default_tags" in tags[0].address


def test_parse_terraform_resolves_local_tags_reference(tmp_path: Path):
    root = tmp_path / "infra" / "aws"
    root.mkdir(parents=True)
    (root / "locals.tf").write_text(
        'locals {\n  tags = {\n    payments = { c4_container = "payments" }\n  }\n}\n',
        encoding="utf-8",
    )
    (root / "main.tf").write_text(
        'resource "aws_lambda_function" "payments" {\n  tags = local.tags.payments\n}\n',
        encoding="utf-8",
    )

    tags = c4_drift.parse_terraform(tmp_path / "infra")

    assert len(tags) == 1
    assert tags[0].container == "payments"
    assert tags[0].address.endswith("aws_lambda_function.payments")


pytestmark_helm = pytest.mark.skipif(shutil.which("helm") is None, reason="helm is not on PATH")


@pytestmark_helm
def test_happy_path_over_the_real_repository():
    exit_code = c4_drift.main(["--repo-root", str(REPO_ROOT)])

    assert exit_code == 0
