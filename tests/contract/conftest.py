"""Shared fixtures for the Redpanda-backed Kafka contract tests (M7a).

Every test in `tests/contract/` is marked `contract` (excluded from the
default `pytest` run by `addopts = "-q -m 'not contract'"` in pyproject.toml)
and skipped outright when Docker isn't reachable, mirroring the
`shutil.which("helm") is None` skip in `tests/bank/k8s/test_helm_chart.py`.
"""

from __future__ import annotations

from collections.abc import Iterator

import docker
import pytest
from testcontainers.community.kafka import RedpandaContainer

_REDPANDA_IMAGE = "redpandadata/redpanda:v25.3.17"


def docker_available() -> bool:
    try:
        docker.from_env().ping()
        return True
    except Exception:
        return False


@pytest.fixture(scope="module")
def bootstrap() -> Iterator[str]:
    with RedpandaContainer(_REDPANDA_IMAGE) as redpanda:
        # Force IPv4: some Docker hosts resolve "localhost" to the IPv6
        # loopback first, and librdkafka pays a slow (~20s) connect timeout
        # per client on that address before falling back to IPv4.
        yield redpanda.get_bootstrap_server().replace("localhost", "127.0.0.1")
