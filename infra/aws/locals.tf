# Shared names and the per-container tag the C4 drift check keys on
# (docs/c4/workspace.dsl deployment view).

locals {
  api_domain     = "api.${var.domain}"
  console_origin = "https://${var.domain}"

  tags = {
    store       = { c4_container = "store" }
    queue       = { c4_container = "queue" }
    alarms      = { c4_container = "alarms" }
    ingest      = { c4_container = "ingest" }
    api         = { c4_container = "api" }
    worker      = { c4_container = "worker" }
    console     = { c4_container = "console" }
    secrets     = { c4_container = "secrets" }
    payments    = { c4_container = "payments" }
    ledger      = { c4_container = "ledger" }
    auth        = { c4_container = "auth" }
    faults      = { c4_container = "faults" }
    ledgerQueue = { c4_container = "ledgerQueue" }
    ops         = { c4_container = "ops" }
    sloReporter = { c4_container = "sloReporter" }
    dashboard   = { c4_container = "dashboard" }
    dns         = { c4_container = "dns" }

    knownIssuesBucket = { c4_container = "knownIssuesBucket" }
    knownIssuesExport = { c4_container = "knownIssuesExport" }
  }
}
