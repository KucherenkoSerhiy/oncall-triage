# Applied once by a human after `az login`. Creates the resource group the
# Azure root module deploys into and the identity GitHub Actions federates
# to - no client secret is ever created.

provider "azurerm" {
  features {}
}

provider "azuread" {}

data "azurerm_client_config" "current" {}

locals {
  tags = {
    project     = var.project
    env         = var.environment
    owner       = "serhiy"
    cost_center = "portfolio"
    managed_by  = "terraform/bootstrap"
  }

  federated_subjects = {
    pull-request = "repo:${var.github_repository}:pull_request"
    master       = "repo:${var.github_repository}:ref:refs/heads/master"
    main         = "repo:${var.github_repository}:ref:refs/heads/main"
    environment  = "repo:${var.github_repository}:environment:${var.environment}"
  }
}

resource "azurerm_resource_group" "main" {
  name     = "rg-${var.project}-${var.environment}"
  location = var.location
  tags     = local.tags
}

resource "azuread_application" "github" {
  display_name = "${var.project}-${var.environment}-github-deploy"
}

resource "azuread_service_principal" "github" {
  client_id = azuread_application.github.client_id
}

resource "azuread_application_federated_identity_credential" "github" {
  for_each = local.federated_subjects

  application_id = azuread_application.github.id
  display_name   = "github-${each.key}"
  description    = "GitHub Actions OIDC: ${each.value}"
  audiences      = ["api://AzureADTokenExchange"]
  issuer         = "https://token.actions.githubusercontent.com"
  subject        = each.value
}

# Contributor on the project resource group only - not on the subscription.
resource "azurerm_role_assignment" "github_contributor" {
  scope                = azurerm_resource_group.main.id
  role_definition_name = "Contributor"
  principal_id         = azuread_service_principal.github.object_id
}

# Resource-group budgets are read through Cost Management; grant just that
# at subscription scope so the deploy identity can manage the budget.
resource "azurerm_role_assignment" "github_cost_management" {
  scope                = "/subscriptions/${data.azurerm_client_config.current.subscription_id}"
  role_definition_name = "Cost Management Contributor"
  principal_id         = azuread_service_principal.github.object_id
}
