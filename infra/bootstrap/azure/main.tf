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
  # the immutable repo:owner@id/repo@id that newer repositories emit. Two
  # flat maps merged directly (not a `merge([for...])` over a list of
  # maps) - checkov's Terraform graph renderer cannot resolve a for_each
  # built through the list-of-maps form and leaves `subject` as the
  # literal string `each.value`, which fails CKV_AZURE_249 unconditionally
  # regardless of the actual subjects.
  classic_subjects = {
    "classic-master"      = "repo:${var.github_repository}:ref:refs/heads/master"
    "classic-main"        = "repo:${var.github_repository}:ref:refs/heads/main"
    "classic-environment" = "repo:${var.github_repository}:environment:${var.environment}"
    "classic-plan"        = "repo:${var.github_repository}:environment:${var.plan_environment}"
  }

  immutable_subjects = {
    "immutable-master"      = "repo:${var.github_repository_immutable}:ref:refs/heads/master"
    "immutable-main"        = "repo:${var.github_repository_immutable}:ref:refs/heads/main"
    "immutable-environment" = "repo:${var.github_repository_immutable}:environment:${var.environment}"
    "immutable-plan"        = "repo:${var.github_repository_immutable}:environment:${var.plan_environment}"
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
  # M9d: PR plans present the `environment:plan` subject instead of the
  # bare `pull_request` one - CKV_AZURE_249 (flags an unscoped pull_request
  # subject) now passes with no skip, since every credential here is pinned
  # to either a ref or a named environment. Fork PRs never receive an
  # id-token for an environment-scoped subject (GitHub requires a branch of
  # this repository to run in a protected environment), so this identity
  # (Contributor on a single resource group) is unreachable from a fork.
  for_each = local.classic_subjects

  application_id = azuread_application.github.id
  display_name   = "github-${each.key}"
  description    = "GitHub Actions OIDC: ${each.value}"
  audiences      = ["api://AzureADTokenExchange"]
  issuer         = "https://token.actions.githubusercontent.com"
  subject        = each.value
}

resource "azuread_application_federated_identity_credential" "github_immutable" {
  # Separate resource (not merged into azuread_application_federated_identity_credential.github
  # above) purely because of a checkov limitation: CKV_AZURE_249's own
  # `gh_repo_regex` (checkov/common/util/oidc_utils.py, same on the
  # bridgecrewio/checkov main branch as of 2026-09) only accepts
  # `[a-zA-Z0-9_-]` for the repo-owner segment, so it rejects GitHub's
  # April-2026 *immutable* subject format (`repo:owner@ownerId/repo@repoId:...`,
  # https://github.blog/changelog/2026-04-23-immutable-subject-claims-for-github-actions-oidc-tokens/)
  # as an invalid repo reference, independent of what the subject actually
  # pins to. Verified directly against checkov's regex (a plain Python
  # `gh_repo_regex.match()` call, no Terraform involved) that no subject
  # containing `owner@id` can ever pass this check as currently
  # implemented - restructuring the Terraform cannot change that. Dropping
  # the immutable subject instead is not an option: this repository
  # issues the immutable subject unconditionally (ADR 0008), so every
  # push/apply to `master`/`demo` would lose Azure OIDC auth entirely.
  # The `github` resource above (classic subjects) carries no skip and
  # passes CKV_AZURE_249 unskipped.
  #checkov:skip=CKV_AZURE_249:immutable subject (repo:owner@id/repo@id, mandatory - see ADR 0008) is rejected by checkov's own repo-format regex, which predates and has no support for GitHub's April 2026 immutable subject claims; upstream checkov limitation, not a policy exception for this credential's actual scope
  for_each = local.immutable_subjects

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
