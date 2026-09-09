"""Azure Functions app (Python v2 programming model): alert-forwarder.

See ``notifications.py``'s sibling ``function_app.py`` for why the
``forwarder`` import below tries a plain import first and falls back to the
fully qualified one.
"""

from __future__ import annotations

import json
import logging
import os

import azure.functions as func

try:
    import forwarder as _logic
except ImportError:
    from bank.azure.alert_forwarder import forwarder as _logic

logger = logging.getLogger(__name__)

app = func.FunctionApp()


@app.function_name(name="forward")
@app.route(route="alerts", methods=["POST"], auth_level=func.AuthLevel.FUNCTION)
def forward(req: func.HttpRequest) -> func.HttpResponse:
    try:
        payload = req.get_json()
    except ValueError:
        return func.HttpResponse(
            json.dumps({"error": "invalid JSON body"}),
            status_code=400,
            mimetype="application/json",
        )

    ingest_url = os.environ.get("INGEST_URL", _logic.DEFAULT_INGEST_URL)
    secret = os.environ.get("INGEST_HMAC_SECRET", "").encode()

    try:
        result = _logic.forward(payload, ingest_url, secret)
    except ValueError as exc:
        return func.HttpResponse(
            json.dumps({"error": str(exc)}), status_code=400, mimetype="application/json"
        )

    if 200 <= result.status < 300:
        return func.HttpResponse(status_code=202)
    return func.HttpResponse(
        json.dumps({"ingest_status": result.status}),
        status_code=502,
        mimetype="application/json",
    )
