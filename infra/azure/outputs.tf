output "resource_group_name" {
  description = "Resource group every Azure resource of the demo lives in."
  value       = data.azurerm_resource_group.main.name
}
