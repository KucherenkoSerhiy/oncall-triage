"""Three-role oncall log triage workflow: triage -> researcher | reporter."""

from google.adk.agents import Agent

from .tools import check_known, get_logs, remember_issue

MODEL = "gemini-flash-latest"

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
        "triage hands you a researcher characterization for a new error."
    ),
)

triage = Agent(
    name="triage",
    model=MODEL,
    description=(
        "Root oncall triage agent. Pulls service logs and checks each error "
        "against the known-issues store, then routes to researcher or "
        "reporter."
    ),
    instruction=(
        "You are the oncall triage agent. When asked to check a service's "
        "logs:\n"
        "1. Call get_logs(service) to fetch recent error lines.\n"
        "2. For each error line, call check_known(error_text) against the "
        "known-issues store.\n"
        "3. Decide, per error:\n"
        "   - KNOWN match (check_known returns known=true): transfer "
        "directly to the reporter sub-agent with the error text and the "
        "stored explanation. Do NOT involve the researcher - the issue is "
        "already explained, so no investigation is needed.\n"
        "   - NEW error (check_known returns known=false): transfer to the "
        "researcher sub-agent first to get a characterization (cause "
        "category, severity guess, next diagnostic step), then pass the "
        "error plus that characterization to the reporter sub-agent to "
        "produce the final report.\n"
        "4. If the user is teaching you about an error instead of asking "
        "for a check - e.g. 'the X error in service Y is expected, because "
        "Z' - call remember_issue(error_pattern, explanation) to store it, "
        "and confirm briefly. Do not involve researcher or reporter for "
        "this case.\n"
        "Always let the reporter produce the final user-facing text; never "
        "write the final report yourself."
    ),
    tools=[get_logs, check_known, remember_issue],
    sub_agents=[researcher, reporter],
)

root_agent = triage
