"""Three-role oncall log triage workflow: triage -> researcher | reporter."""

from google.adk.agents import Agent

from .model import build_model
from .tools import check_known, get_alert, get_recent_alerts, remember_issue

MODEL = build_model()

researcher = Agent(
    name="researcher",
    model=MODEL,
    description=(
        "Investigates a genuinely NEW log error (one with no match in the "
        "known-issues store) and produces a short characterization from the "
        "error text alone: likely cause category, severity guess, and a "
        "suggested next diagnostic step. Use this agent only when triage has "
        "determined the error is new, never for already-known errors."
    ),
    instruction=(
        "You are the researcher. You receive a single new, unexplained log "
        "error. Using only reasoning over the error text (no external "
        "services or tools), produce a short characterization with exactly "
        "three parts:\n"
        "1. Likely cause category (e.g. resource exhaustion, bad input, "
        "downstream dependency failure, code defect, config/auth issue).\n"
        "2. Severity guess (low / medium / high) with a one-clause reason.\n"
        "3. Suggested next diagnostic step (a concrete, specific action).\n"
        "Keep it brief. Hand your characterization back so the reporter can "
        "build the final report."
    ),
)

reporter = Agent(
    name="reporter",
    model=MODEL,
    description=(
        "Formats the final answer shown to the oncall engineer. Use this "
        "agent last, always, whether the error turned out to be known or "
        "new — it produces the actual response text."
    ),
    instruction=(
        "You are the reporter. You produce the final message shown to the "
        "oncall engineer, and there are exactly two output formats:\n\n"
        "FORMAT A - known issue: Output ONE terse line citing the stored "
        "explanation, with no alarm and no recommendation to page. Example: "
        "'Known issue: <pattern> - <explanation>.'\n\n"
        "FORMAT B - new issue: Output a fuller report with three labeled "
        "sections: the error text, the researcher's characterization "
        "(cause category, severity guess, next diagnostic step), and a "
        "closing recommendation of whether to page oncall now or monitor.\n\n"
        "Never mix the two formats. Use FORMAT A only when triage tells you "
        "the error matched the known-issues store; use FORMAT B only when "
        "triage hands you a researcher characterization for a new error.\n\n"
        "Whichever format you use, always END your reply with a fenced "
        "block, and nothing after it, exactly like:\n"
        "```verdict\n"
        '{"known": false, "severity": "sev2", "action": "page", "summary": "one line"}\n'
        "```\n"
        "where known mirrors what triage found (true for FORMAT A, false for "
        "FORMAT B), severity is the alert's severity (sev1/sev2/sev3/sev4), "
        'action is one of "page", "monitor", "ack", and summary is one short '
        "line summarizing the verdict."
    ),
)

triage = Agent(
    name="triage",
    model=MODEL,
    description=(
        "Root oncall triage agent. Pulls the alert and checks its error "
        "against the known-issues store, then routes to researcher or "
        "reporter."
    ),
    instruction=(
        "You are the oncall triage agent. When asked to triage an alert:\n"
        "1. Call get_alert(alert_id) to fetch its full details (service, "
        "title, description, sample error lines).\n"
        "2. You may call get_recent_alerts(service) to see whether this "
        "service has been noisy recently, if that context would help.\n"
        "3. Call check_known(service, error_text) against the known-issues "
        "store for the alert's error text.\n"
        "4. Decide:\n"
        "   - KNOWN match (check_known returns known=true): transfer "
        "directly to the reporter sub-agent with the error text and the "
        "stored explanation. Do NOT involve the researcher - the issue is "
        "already explained, so no investigation is needed.\n"
        "   - NEW error (check_known returns known=false): transfer to the "
        "researcher sub-agent first to get a characterization (cause "
        "category, severity guess, next diagnostic step), then pass the "
        "error plus that characterization to the reporter sub-agent to "
        "produce the final report.\n"
        "5. If the user is teaching you about an error instead of asking "
        "for a check - e.g. 'the X error in service Y is expected, because "
        "Z' - call remember_issue(service, error_pattern, explanation) to "
        "store it, and confirm briefly. Do not involve researcher or "
        "reporter for this case.\n"
        "Always let the reporter produce the final user-facing text; never "
        "write the final report yourself."
    ),
    tools=[get_alert, get_recent_alerts, check_known, remember_issue],
    sub_agents=[researcher, reporter],
)

root_agent = triage
