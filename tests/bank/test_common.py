from __future__ import annotations

from bank.aws.common import current_fault
from tests.bank.conftest import put_fault


def test_current_fault_is_none_when_no_item(moto_infra):
    assert current_fault("payments") is None


def test_current_fault_returns_mode_while_active(moto_infra):
    put_fault(moto_infra, "payments", "errors", minutes=5)

    assert current_fault("payments") == "errors"


def test_current_fault_is_none_once_expired(moto_infra):
    put_fault(moto_infra, "payments", "errors", minutes=-5)

    assert current_fault("payments") is None
