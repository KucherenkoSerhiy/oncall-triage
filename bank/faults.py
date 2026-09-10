"""Shared fault-mode table for the Kubernetes bank estate's chaos surface.

Mirrors ``bank.aws.common.VALID_MODES`` (the AWS estate's single source of
truth for chaos validation): both ``task chaos-k8s`` (``scripts/chaos_k8s.py``)
and ``bankops chaos --estate kubernetes`` (``cli/bankops/commands.py``)
validate service/mode pairs against this table instead of duplicating it.

The per-service ``VALID_MODES`` tuples in ``bank/k8s/<service>/service.py``
stay separate on purpose: they ship inside each service's Docker image
(``bank/k8s/_shared`` + the service directory only, no repo root), while this
module is a host-side tool used by the CLI and the Taskfile only.
"""

from __future__ import annotations

VALID_MODES: dict[str, tuple[str, ...]] = {
    "cards-authorization": ("timeouts", "issuer-down"),
    "fraud-scoring": ("model-drift", "latency", "crashloop", "lag"),
    "open-banking-api": ("rate-limit-storm", "cert-expiry"),
}
