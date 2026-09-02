#!/usr/bin/env bash
# Three-act demo: research a new error, teach it, watch it short-circuit.
# Isolated store copy — the repo's known_issues.json is never touched.
# Requires: adk on PATH (or edit ADK below), GOOGLE_API_KEY in oncall_triage/.env
set -euo pipefail
cd "$(dirname "$0")"

ADK="${ADK:-adk}"
DEMO_STORE="$(pwd)/demo_store.json"
cp known_issues.json "$DEMO_STORE"
trap 'rm -f "$DEMO_STORE"' EXIT

printf '%s\n' \
  "check inventory-service logs, anything to worry about?" \
  "The StockReconciliationTimeout in inventory-service is expected: warehouse-sync-3 runs a nightly batch that pauses reconciliation. Not an incident, please remember this." \
  "check inventory-service logs again, anything to worry about?" \
| TRIAGE_STORE_PATH="$DEMO_STORE" "$ADK" run oncall_triage

echo
echo "=== store after the demo (note the taught entry) ==="
cat "$DEMO_STORE"
