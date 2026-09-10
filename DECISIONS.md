# Implementation decisions (M9a)

The M9a spec (`docs/specs/m9-hardening.md`, slice 1) is detailed but leaves
some concrete choices open, or names things slightly differently from how
the current repository actually numbers/names them. Recorded here rather
than guessed silently.

- **"`docs/DESIGN.md` section 8" means the Cost model section, which is
  actually numbered 9.** The spec's prose always pairs the number with a
  description - `"docs/DESIGN.md section 8"` and, once, `"section 8 (cost
  model)"` - but `DESIGN.md`'s actual section 8 is "Security posture";
  section 9 is "Cost model". Milestones between when the spec was written
  and today (M7/M7a's Kafka sections) most likely shifted the numbering.
  Treated the parenthetical description as authoritative over the number
  and updated section 9 (Cost model): the alarm count, the ~$0.10/month
  11th-alarm delta, and a link to `docs/slo.md`.
- **The 11th-alarm delta is ~$0.10/month, not the "~$0.30/month" requirement
  8 names.** The spec's own intro paragraph gives the correct figure
  ("accept ~$0.10/month per extra alarm"), matching real CloudWatch
  pricing: $0.10/alarm-month for *standard*-resolution alarms (period >=
  60s, what all five ops alarms use) beyond the free 10, versus
  $0.30/alarm-month only for *high-resolution* alarms (period < 60s) -
  none of these are. `$0.30` is also the exact figure the pre-existing
  `docs/DESIGN.md` Cost model table already used for an 11th *custom
  metric* (a different line item), which is almost certainly what
  requirement 8 actually reused by mistake. Went with the intro
  paragraph's (and reality's) $0.10.
- **Accepted the 11th alarm's ~$0.10/month rather than combining alarms
  via metric math.** The spec offers both options explicitly. Six bank
  alarms (M4) + five ops alarms (this slice) = 11, one over the
  always-free 10. Combining, say, `WorkerErrors` and `WorkerDurationP95`
  behind one metric-math alarm (an `OR` of two `IF()` breach expressions)
  would claw the count back to 10, but the resulting alarm can't say
  *which* signal breached without a second look at the underlying metrics
  - exactly the ambiguity `alarms.tf`'s existing `AlarmDescription`
    convention (`service=<name>; <sentence>`) exists to avoid. Five
  separately-named, separately-actionable alarms are worth the dime;
  documented in `docs/DESIGN.md` section 9 and `infra/README.md`.
- **The ops topic's human subscriber is `oncall`, not `operator`, in the
  C4 model.** The spec's requirement 8 says "ops alarms -> ops topic ->
  operator" using lower-case, generic "operator". `docs/c4/workspace.dsl`
  already has two people: `oncall` ("On-call engineer", reads verdicts on
  the console) and `operator` ("Chaos operator", runs `bankops` to inject
  faults) - a different role. The ops topic's e-mail subscription pages
  the person who reads dashboards and consoles, i.e. `oncall`, not the one
  firing synthetic faults, so the relationship is `triage.ops -> oncall`.
- **"ops alarms" is modeled as each alarmed-on container feeding
  `triage.ops` directly, not as a separate "ops alarms" element.** First
  pass wrongly routed the relationship through the dashboard
  (`triage.dashboard -> triage.ops`) - the dashboard only visualizes
  metrics, it doesn't fire alarms. Fixed to mirror the existing
  `awsEstate.alarms` pattern exactly: `awsEstate.payments/ledger/auth ->
  awsEstate.alarms "alarm state change"` has the *sources* feed the SNS
  topic container directly, with no separate "alarms" element in between.
  `triage.ingest`, `triage.worker` and `triage.queue` (the three
  containers the five ops alarms actually watch) now feed
  `triage.ops "alarm state change (...)"` the same way, each relationship
  naming which of the five alarms it stands for.
- **`SloAttainment` (and `VerdictLatencyP95`) are skipped, not published as
  0, on a day with zero triaged alerts.** The spec's test list only pins
  down "an empty day publishes `AlertsTriaged=0` and no p95" - it's silent
  on `SloAttainment`. Publishing `SloAttainment=0` on a quiet day would
  read as "0% of alerts met their SLO" on the dashboard, which misstates
  "there were no alerts to measure". `build_report()` returns `attainment:
  None` when the day's triaged-alert count is 0, and
  `_publish_metrics()` omits both `VerdictLatencyP95` and `SloAttainment`
  from the `PutMetricData` call whenever their value is `None`, publishing
  only `AlertsTriaged=0`.
- **`by_status` GSI + a `received_at BETWEEN` key condition, no new
  `by_day` GSI.** The spec offers both options ("query the `by_status`
  index for `triaged` items then filter by date - or add a GSI `by_day`
  if the scan would be unbounded"). `by_status`'s range key is already
  `received_at`, so a `Query` with `#status = "triaged" AND received_at
  BETWEEN <yesterday 00:00Z> AND <today 00:00Z>` returns exactly
  yesterday's triaged alerts directly from DynamoDB - no client-side date
  filtering over an unbounded result set, and no new index/write-capacity
  cost. See the docstring in `bank/ops/slo_reporter/handler.py`.
- **p95 by nearest-rank, no new dependency.** `_p95()` sorts the day's
  latencies and picks `round(0.95 * (n-1))` - standard nearest-rank
  percentile, matching what a handful of daily data points actually
  supports (no interpolation library pulled in for a Lambda that runs
  once a day over single-digit-to-low-hundreds of rows).
- **The error budget's "alerts per day" figure is `var.daily_alert_cap`
  (500), not a measured live volume.** Nothing in the repository documents
  actual historical daily alert volume (the estate is chaos-driven and
  bursty, not continuous production traffic), so `docs/slo.md` grounds the
  30-day/5% budget against the one concrete, already-documented ceiling
  (`docs/DESIGN.md` section 9's "worker refuses to call the model past 500
  alerts/day") as a worst case, while noting actual demo volume is a small
  fraction of it.
- **README "what a reviewer should look at" section created in this
  slice.** M9a's own requirement 4 says to link `docs/slo.md` from it, but
  that section is really `docs/specs/m9-hardening.md` requirement 7's
  README demo-script work, out of scope for slice 1 (which covers
  requirements 1, the alarm half of 2, 8 and 9 only). Added a minimal,
  honest version now (tests, Terraform gates, design docs, self-
  observability) rather than leaving the requirement-4 link dangling; a
  note in the section says runbooks and the C4 drift gate land in later
  M9 slices.
