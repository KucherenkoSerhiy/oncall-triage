"""Azure Functions app (Python v2 programming model): customer-notifications.

Deploys standalone, zipped from this directory alone (M5b). Azure's Python
worker adds the app's own directory to ``sys.path`` and imports this file as
a top-level module - not as part of the ``bank.azure.customer_notifications``
package - so ``notifications`` resolves as a plain sibling import there. In
the repo (and under pytest) this file is imported as part of that package
instead, so the plain import fails and we fall back to the fully qualified
one. Same trick as ``bank/azure/alert_forwarder/function_app.py``.
"""

from __future__ import annotations

import logging
import os

import azure.functions as func

try:
    import notifications as _logic
except ImportError:
    from bank.azure.customer_notifications import notifications as _logic

logger = logging.getLogger(__name__)

app = func.FunctionApp()

_connection_string = os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING")
if _connection_string:
    from azure.monitor.opentelemetry import configure_azure_monitor

    configure_azure_monitor(connection_string=_connection_string)

_chaos_client = _logic.ChaosClient(
    chaos_url=os.environ.get("CHAOS_URL", _logic.DEFAULT_CHAOS_URL),
    token=os.environ.get("CONSOLE_TOKEN"),
)


@app.function_name(name="send_batch")
@app.timer_trigger(schedule="0 * * * * *", arg_name="timer", run_on_startup=False)
def send_batch(timer: func.TimerRequest) -> None:
    mode = _chaos_client.current_mode()
    _logic.send_batch(mode, _logic.AppInsightsMetrics())
