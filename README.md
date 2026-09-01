# oncall-triage

A three-role agent workflow, built on Google ADK, that triages service log
errors: it recognizes previously-explained known issues, researches
genuinely new ones, and reports with a verbosity matched to the case.

## Roles and flow

- **triage** (root agent) — pulls logs for a service via `get_logs` and
  checks each error against the known-issues store via `check_known`.
  - Known match → hands off directly to **reporter**.
  - New error → hands off to **researcher** first, then **reporter**.
  - The routing is genuine ADK dynamic delegation (`sub_agents` +
    description-driven transfer), not a fixed sequential pipeline — the
    model decides which sub-agent to invoke based on what `check_known`
    returned.
- **researcher** (sub-agent) — given a new error's text, reasons out a
  short characterization: likely cause category, severity guess, and a
  suggested next diagnostic step. No external services, reasoning only.
- **reporter** (sub-agent) — formats the final answer:
  - Known issue → one terse line citing the stored explanation, no alarm.
  - New issue → a fuller report: the error, the researcher's
    characterization, and a recommendation to page or monitor.

You can also teach the system: a message like "the connection pool
exhausted error in payments-service is expected, because it's a known
scaling limit" causes triage to call `remember_issue` and persist it to
the known-issues store.

## Known-issues store

A local JSON file, `known_issues.json` in the repo root by default
(override with the `TRIAGE_STORE_PATH` env var). It ships pre-seeded with
one known issue (`connection pool exhausted`) so the known-issue path is
demonstrable immediately. A production deployment would swap this for
Vertex AI Memory Bank; that's out of scope here.

## Sequence diagrams

### Known-issue path

```mermaid
sequenceDiagram
    actor U as Oncall Engineer
    participant T as triage
    participant S as known_issues.json
    participant R as reporter

    U->>T: "check payments-service logs"
    T->>T: get_logs("payments-service")
    T->>S: check_known(error_text)
    S-->>T: known=true, explanation
    T->>R: hand off (error + stored explanation)
    R-->>U: terse one-line report, no alarm
```

### New-issue path

```mermaid
sequenceDiagram
    actor U as Oncall Engineer
    participant T as triage
    participant S as known_issues.json
    participant Res as researcher
    participant R as reporter

    U->>T: "check inventory-service logs"
    T->>T: get_logs("inventory-service")
    T->>S: check_known(error_text)
    S-->>T: known=false
    T->>Res: hand off (new error text)
    Res-->>T: characterization (cause, severity, next step)
    T->>R: hand off (error + characterization)
    R-->>U: full report + page/monitor recommendation
```

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # then fill in GOOGLE_API_KEY
```

## Run

From the repo root:

```bash
adk web
```

or:

```bash
adk run oncall_triage
```

Then try prompts like:

- "check payments-service logs" (known-issue path)
- "check inventory-service logs" (new-issue path)
- "the NullPointerException in RefundCalculator error in
  payments-service is expected, because it's a known null-safety bug
  with a fix scheduled" (teaches a new known issue)

No API key is required to import the agent module or run the test suite —
only actually talking to the model (via `adk web`/`adk run`) needs
`GOOGLE_API_KEY`.

## Tests

```bash
pytest
```

All tests are structural/wiring checks (agent wiring, tool behavior,
store persistence, instruction content) — none of them make a live model
call or require an API key.
