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

  # Entra federated credentials match the subject exactly (no wildcards), so
  # both GitHub subject forms are registered: classic repo:owner/repo and
  # the immutable repo:owner@id/repo@id that newer repositories emit.
  federated_subjects = merge([
    for key, repo in { classic = var.github_repository, immutable = var.github_repository_immutable } : {
      "${key}-pull-request"    = "repo:${repo}:pull_request"
      "${key}-master"          = "repo:${repo}:ref:refs/heads/master"
      "${key}-main"            = "repo:${repo}:ref:refs/heads/main"
      "${key}-environment"     = "repo:${repo}:environment:${var.environment}"
    }
  ]...)
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
  # The pull_request subject lets pull requests of THIS repository (pinned by
  # name and by immutable id) run `terraform plan`; the identity is
  # Contributor on a single resource group and fork PRs never receive an
  # id-token. Moving PR plans to an environment-scoped subject on both
  # clouds is scheduled for M9 (needs a bootstrap credential session).
  #checkov:skip=CKV_AZURE_249:pull_request subject is pinned to this repository; environment-scoped subject planned for M9
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
