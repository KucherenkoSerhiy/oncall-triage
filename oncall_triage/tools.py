"""Plain-Python tools used by the triage agent."""

from . import store

# Mock log store: at least 3 services, each mixing a known-class error
# (matches known_issues.json) with a genuinely new-class error.
_MOCK_LOGS = {
    "payments-service": [
        "ERROR 2026-09-01T10:00:00Z connection pool exhausted while processing checkout batch",
        "ERROR 2026-09-01T10:04:12Z NullPointerException in RefundCalculator.applyDiscount",
    ],
    "auth-service": [
        "ERROR 2026-09-01T09:55:03Z connection pool exhausted during token refresh burst",
        "ERROR 2026-09-01T09:58:47Z JWT signature verification failed: unknown key id kid-77",
    ],
    "inventory-service": [
        "ERROR 2026-09-01T08:30:11Z StockReconciliationTimeout waiting on warehouse-sync-3",
        "ERROR 2026-09-01T08:41:02Z connection pool exhausted while syncing SKU deltas",
    ],
}


def get_logs(service: str) -> list[str]:
    """Fetch recent error log lines for a service.

    Returns a friendly one-item list (never raises) if the service is unknown.
    """
    if service not in _MOCK_LOGS:
        known = ", ".join(sorted(_MOCK_LOGS.keys()))
        return [f"No logs found for service '{service}'. Known services: {known}."]
    return list(_MOCK_LOGS[service])


def check_known(error_text: str) -> dict:
    """Check whether error_text matches a previously-explained known issue."""
    match = store.find_known(error_text)
    if match is None:
        return {"known": False, "pattern": None, "explanation": None}
    return {"known": True, "pattern": match["pattern"], "explanation": match["explanation"]}


def remember_issue(error_pattern: str, explanation: str) -> dict:
    """Persist a new known-issue pattern and its explanation to the store."""
    record = store.add_known(error_pattern, explanation)
    return {"stored": True, "pattern": record["pattern"], "explanation": record["explanation"]}
