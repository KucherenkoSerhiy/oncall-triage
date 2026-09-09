"""Renders a `prometheus_client` registry as an HTTP `/metrics` response body."""

from __future__ import annotations

from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, generate_latest


def render(registry: CollectorRegistry) -> tuple[bytes, str]:
    """Return `(body, content_type)` for a `/metrics` response."""
    return generate_latest(registry), CONTENT_TYPE_LATEST
