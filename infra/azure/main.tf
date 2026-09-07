provider "azurerm" {
  features {}
  # The deploy identity is Contributor on one resource group, not the
  # subscription, so it cannot register resource providers; the bootstrap
  # identity registers what the design needs.
  resource_provider_registrations = "none"
}

locals {
  name_prefix = "${var.project}-${var.environment}"
}

# Created by infra/bootstrap/azure; the deploy identity is Contributor here.
data "azurerm_resource_group" "main" {
  name = "rg-${local.name_prefix}"
}

# ---------------------------------------------------------------- guardrail

resource "azurerm_consumption_budget_resource_group" "monthly" {
  name              = "${local.name_prefix}-monthly"
  resource_group_id = data.azurerm_resource_group.main.id
  amount            = var.monthly_budget_usd
  time_grain        = "Monthly"

  time_period {
    start_date = "2026-09-01T00:00:00Z"
  }

  notification {
    enabled        = true
    threshold      = 80
    operator       = "GreaterThan"
    threshold_type = "Actual"
    contact_emails = [var.notification_email]
  }

  notification {
    enabled        = true
    threshold      = 100
    operator       = "GreaterThan"
    threshold_type = "Forecasted"
    contact_emails = [var.notification_email]
  }
}
