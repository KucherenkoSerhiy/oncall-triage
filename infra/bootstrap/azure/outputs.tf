output "client_id" {
  description = "Set as the GitHub repository variable AZURE_CLIENT_ID."
  value       = azuread_application.github.client_id
}

output "tenant_id" {
  description = "Set as the GitHub repository variable AZURE_TENANT_ID."
  value       = data.azurerm_client_config.current.tenant_id
}

output "subscription_id" {
  description = "Set as the GitHub repository variable AZURE_SUBSCRIPTION_ID."
  value       = data.azurerm_client_config.current.subscription_id
}

output "resource_group_name" {
  description = "Resource group the Azure root module deploys into."
  value       = azurerm_resource_group.main.name
}
