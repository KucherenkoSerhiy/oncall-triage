"""Minimal `http.server`-based HTTP app for alerts-bridge.

Three routes: `GET /healthz` -> `200 ok`, `GET /metrics` -> Prometheus
exposition text, `POST /alertmanager` -> runs `service.handle_webhook` on the
parsed JSON body and answers with the status it returns (202 / 500). Not
`_shared/server.py`'s generic `/work` shape - this service's one job is the
webhook.
"""

from __future__ import annotations

import json
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from prometheus_client import CollectorRegistry

try:
    from _shared.metrics import render
except ImportError:
    from bank.k8s._shared.metrics import render

from .service import AlertsBridgeService

logger = logging.getLogger(__name__)


def make_handler(
    service: AlertsBridgeService, registry: CollectorRegistry
) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def _respond(self, status: int, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            if self.path == "/healthz":
                self._respond(200, b"ok", "text/plain; charset=utf-8")
            elif self.path == "/metrics":
                body, content_type = render(registry)
                self._respond(200, body, content_type)
            else:
                self._respond(404, b"not found", "text/plain; charset=utf-8")

        def do_POST(self) -> None:
            if self.path != "/alertmanager":
                self._respond(404, b"not found", "text/plain; charset=utf-8")
                return
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length) or b"{}")
            status = service.handle_webhook(payload)
            self._respond(status, b"", "text/plain; charset=utf-8")

        def log_message(self, format: str, *args: object) -> None:
            logger.info("%s - %s", self.address_string(), format % args)

    return Handler


def run(
    service: AlertsBridgeService, registry: CollectorRegistry, port: int = 8080
) -> ThreadingHTTPServer:
    handler = make_handler(service, registry)
    return ThreadingHTTPServer(("0.0.0.0", port), handler)  # noqa: S104 - binds all interfaces inside the pod on purpose
