output "resource_group_name" {
  description = "Resource group every Azure resource of the demo lives in."
  value       = data.azurerm_resource_group.main.name
}

output "forwarder_url" {
  description = "The alert forwarder's HTTP-trigger URL, including its default function key - what the action group's webhook calls."
  value       = local.forwarder_url
  sensitive   = true
}

output "notifications_app_name" {
  description = "Name of the customer-notifications Function app."
  value       = azurerm_linux_function_app.notifications.name
}

output "action_group_id" {
  description = "Resource id of the alert action group the three rules fire into."
  value       = azurerm_monitor_action_group.alerts.id
}

output "alert_rule_names" {
  description = "Names of the three Azure Monitor rules watching customer-notifications."
  value = [
    azurerm_monitor_metric_alert.notifications_failures.name,
    azurerm_monitor_scheduled_query_rules_alert_v2.provider_429.name,
    azurerm_monitor_scheduled_query_rules_alert_v2.backlog.name,
  ]
}
