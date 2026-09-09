"""Prove the Function apps import cleanly under ``azure.functions``.

Decorators like ``@app.timer_trigger`` / ``@app.route`` are inert without
the Functions host, but importing the modules exercises the module-level
``func.FunctionApp()`` wiring and the sibling-import fallback documented in
each ``function_app.py``.
"""

from __future__ import annotations


def test_customer_notifications_function_app_loads():
    from bank.azure.customer_notifications import function_app

    functions = function_app.app.get_functions()
    assert [f.get_function_name() for f in functions] == ["send_batch"]
    assert functions[0].get_trigger().type == "timerTrigger"


def test_alert_forwarder_function_app_loads():
    from bank.azure.alert_forwarder import function_app

    functions = function_app.app.get_functions()
    assert [f.get_function_name() for f in functions] == ["forward"]
    assert functions[0].get_trigger().type == "httpTrigger"
