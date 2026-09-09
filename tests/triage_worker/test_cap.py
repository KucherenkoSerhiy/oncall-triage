from __future__ import annotations

import boto3

from services.triage_worker.cap import DailyCap


def _verdicts_table(moto_infra):
    return boto3.resource("dynamodb", region_name=moto_infra["region"]).Table(
        moto_infra["verdicts_table"]
    )


def test_try_acquire_succeeds_up_to_cap_then_denies(moto_infra, monkeypatch):
    monkeypatch.setenv("DAILY_ALERT_CAP", "3")
    cap = DailyCap(_verdicts_table(moto_infra))
    today = "2026-09-09"

    assert cap.try_acquire(today) is True
    assert cap.try_acquire(today) is True
    assert cap.try_acquire(today) is True
    assert cap.try_acquire(today) is False


def test_501st_call_in_a_day_is_capped(moto_infra, monkeypatch):
    monkeypatch.setenv("DAILY_ALERT_CAP", "500")
    cap = DailyCap(_verdicts_table(moto_infra))
    today = "2026-09-09"

    for _ in range(500):
        assert cap.try_acquire(today) is True

    assert cap.try_acquire(today) is False


def test_new_day_resets_the_cap(moto_infra, monkeypatch):
    monkeypatch.setenv("DAILY_ALERT_CAP", "1")
    cap = DailyCap(_verdicts_table(moto_infra))

    assert cap.try_acquire("2026-09-09") is True
    assert cap.try_acquire("2026-09-09") is False
    assert cap.try_acquire("2026-09-10") is True
