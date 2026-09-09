# Azure Monitor alerting for customer-notifications: one action group whose
# webhook fires into the forwarder Function (function-key auth, so the key
# has to be baked into the webhook URL - data.azurerm_function_app_host_keys
# below), and three rules that watch the notifications app.

data "azurerm_function_app_host_keys" "forwarder" {
  name                = azurerm_linux_function_app.forwarder.name
  resource_group_name = data.azurerm_resource_group.main.name
}

locals {
  # The forwarder's HTTP trigger is function-key authed (auth_level=FUNCTION
  # in function_app.py); the action group has no other way to authenticate,
  # so the default function key rides along in the URL.
  forwarder_url = "https://${azurerm_linux_function_app.forwarder.default_hostname}/api/alerts?code=${data.azurerm_function_app_host_keys.forwarder.default_function_key}"
}

resource "azurerm_monitor_action_group" "alerts" {
  name                = "${local.name_prefix}-alerts"
  resource_group_name = data.azurerm_resource_group.main.name
  short_name          = "nwtriage"

  webhook_receiver {
    name                    = "alert-forwarder"
    service_uri             = local.forwarder_url
    use_common_alert_schema = true
  }

  tags = local.tags.monitor
}

# Timer failures (the provider-429 fault) raise inside send_batch, which
# Application Insights records as an exception - Http5xx on the site would
# miss a timer trigger entirely, since there's no HTTP response to grade.
resource "azurerm_monitor_metric_alert" "notifications_failures" {
  name                = "${local.name_prefix}-customer-notifications-Failures-Sev2"
  resource_group_name = data.azurerm_resource_group.main.name
  scopes              = [azurerm_application_insights.main.id]
  description         = "service=customer-notifications; the timer trigger is raising exceptions (provider-429 fault or a real SMS provider outage)."
  severity            = 2
  frequency           = "PT1M"
  window_size         = "PT5M"

  criteria {
    metric_namespace = "microsoft.insights/components"
    metric_name      = "exceptions/count"
    aggregation      = "Total"
    operator         = "GreaterThanOrEqual"
    threshold        = 3
  }

  action {
    action_group_id = azurerm_monitor_action_group.alerts.id
  }

  tags = local.tags.monitor
}

resource "azurerm_monitor_scheduled_query_rules_alert_v2" "provider_429" {
  name                = "${local.name_prefix}-customer-notifications-Provider429-Sev2"
  resource_group_name = data.azurerm_resource_group.main.name
  location            = data.azurerm_resource_group.main.location
  scopes              = [azurerm_log_analytics_workspace.main.id]
  description         = "service=customer-notifications; the SMS/e-mail provider is returning 429 Too Many Requests (provider-429 fault or a real rate limit)."
  severity            = 2

  evaluation_frequency    = "PT1M"
  window_duration         = "PT5M"
  auto_mitigation_enabled = true

  criteria {
    query                   = "customMetrics | where name == \"provider_429\" | summarize sum(value)"
    time_aggregation_method = "Total"
    threshold               = 20
    operator                = "GreaterThanOrEqual"

    failing_periods {
      minimum_failing_periods_to_trigger_alert = 1
      number_of_evaluation_periods             = 1
    }
  }

  action {
    action_groups = [azurerm_monitor_action_group.alerts.id]
  }

  tags = local.tags.monitor
}

resource "azurerm_monitor_scheduled_query_rules_alert_v2" "backlog" {
  name                = "${local.name_prefix}-customer-notifications-Backlog-Sev3"
  resource_group_name = data.azurerm_resource_group.main.name
  location            = data.azurerm_resource_group.main.location
  scopes              = [azurerm_log_analytics_workspace.main.id]
  description         = "service=customer-notifications; the notifications backlog has grown past 100 (backlog fault or a real provider slowdown)."
  severity            = 3

  evaluation_frequency    = "PT1M"
  window_duration         = "PT5M"
  auto_mitigation_enabled = true

  criteria {
    query                   = "customMetrics | where name == \"notifications_backlog\" | summarize max(value)"
    time_aggregation_method = "Maximum"
    threshold               = 100
    operator                = "GreaterThanOrEqual"

    failing_periods {
      minimum_failing_periods_to_trigger_alert = 1
      number_of_evaluation_periods             = 1
    }
  }

  action {
    action_groups = [azurerm_monitor_action_group.alerts.id]
  }

  tags = local.tags.monitor
}
