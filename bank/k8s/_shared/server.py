"""Minimal `http.server`-based HTTP app shared by the three k8s bank services.

Three routes: `GET /healthz` -> `200 ok`, `GET /metrics` -> Prometheus
exposition text, `GET|POST /work` -> runs one unit of work and returns it as
JSON. No framework beyond the standard library.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from prometheus_client import CollectorRegistry

from .metrics import render

logger = logging.getLogger(__name__)

WorkFn = Callable[[], dict[str, Any]]


def make_handler(work: WorkFn, registry: CollectorRegistry) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def _respond(self, status: int, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _work(self) -> None:
            result = work()
            self._respond(200, json.dumps(result).encode(), "application/json")

        def do_GET(self) -> None:
            if self.path == "/healthz":
                self._respond(200, b"ok", "text/plain; charset=utf-8")
            elif self.path == "/metrics":
                body, content_type = render(registry)
                self._respond(200, body, content_type)
            elif self.path == "/work":
                self._work()
            else:
                self._respond(404, b"not found", "text/plain; charset=utf-8")

        def do_POST(self) -> None:
            if self.path == "/work":
                self._work()
            else:
                self._respond(404, b"not found", "text/plain; charset=utf-8")

        def log_message(self, format: str, *args: object) -> None:
            logger.info("%s - %s", self.address_string(), format % args)

    return Handler


def run(work: WorkFn, registry: CollectorRegistry, port: int = 8080) -> ThreadingHTTPServer:
    handler = make_handler(work, registry)
    return ThreadingHTTPServer(("0.0.0.0", port), handler)  # noqa: S104 - binds all interfaces inside the pod on purpose
