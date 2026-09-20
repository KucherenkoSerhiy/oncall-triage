"""clean_report strips what the console must not show (#126)."""

from services.triage_worker.runner import clean_report

FENCE = (
    '\n```verdict\n{"known": false, "severity": "sev3", "action": "monitor", "summary": "s"}\n```'
)


def test_drops_the_verdict_fence():
    assert clean_report("**Error text:** boom\n**Cause:** x" + FENCE) == (
        "**Error text:** boom\n**Cause:** x"
    )


def test_drops_inline_narration_up_to_the_rule():
    text = (
        "I am now the reporter, and I have received the researcher's characterization. "
        "I will format the final alert message using FORMAT B. --- **Error text:** p99 "
        "latency crossed threshold **Cause:** resource exhaustion" + FENCE
    )
    assert clean_report(text) == (
        "**Error text:** p99 latency crossed threshold **Cause:** resource exhaustion"
    )


def test_drops_multi_sentence_narration_up_to_the_rule():
    text = (
        "I'm the reporter. I've received the researcher's characterization of this new "
        "latency alert. Here is the final oncall response:\n---\n**Error:** spike" + FENCE
    )
    assert clean_report(text) == "**Error:** spike"


def test_drops_narration_up_to_the_first_label_when_there_is_no_rule():
    text = "I am the reporter. I will now produce the report. **Error text:** x **Cause:** y"
    assert clean_report(text + FENCE) == "**Error text:** x **Cause:** y"


def test_format_a_line_is_untouched():
    assert clean_report("Known issue: pool exhausted - auto-recovers." + FENCE) == (
        "Known issue: pool exhausted - auto-recovers."
    )


def test_text_without_narration_or_fence_is_untouched():
    assert clean_report("Recommendation: monitor for now") == "Recommendation: monitor for now"


def test_narration_without_rule_or_label_is_kept_rather_than_emptied():
    assert clean_report("I am the reporter and that is all.") == (
        "I am the reporter and that is all."
    )
