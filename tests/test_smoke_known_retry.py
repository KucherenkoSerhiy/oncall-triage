"""The smoke's known-issue check tolerates one model miss, never a missed match (#113)."""

from scripts.smoke import _KNOWN_VERDICT_ATTEMPTS, known_verdict_acceptable


def test_ack_on_a_known_issue_passes():
    assert known_verdict_acceptable({"known": True, "action": "ack"})


def test_monitor_on_a_known_issue_is_not_accepted_by_itself():
    assert not known_verdict_acceptable({"known": True, "action": "monitor"})


def test_ack_without_a_match_is_not_accepted():
    assert not known_verdict_acceptable({"known": False, "action": "ack"})


def test_exactly_one_retry():
    assert _KNOWN_VERDICT_ATTEMPTS == 2
