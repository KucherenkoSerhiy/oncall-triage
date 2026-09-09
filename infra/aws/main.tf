provider "aws" {
  region = var.region

  default_tags {
    tags = {
      project     = var.project
      env         = var.environment
      owner       = "serhiy"
      cost_center = "portfolio"
      managed_by  = "terraform/aws"
    }
  }
}

locals {
  name_prefix = "${var.project}-${var.environment}"
}

# ---------------------------------------------------------------- guardrail

resource "aws_budgets_budget" "monthly" {
  name         = "${local.name_prefix}-monthly"
  budget_type  = "COST"
  limit_amount = tostring(var.monthly_budget_usd)
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.notification_email]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = [var.notification_email]
  }
}

# ---------------------------------------------------------------- DNS zone
# Delegated from the parent domain by four NS records that Terraform
# writes into the Cloudflare parent zone (see dns_delegation.tf).
# Certificates and records for the console and the API are added with
# the alert spine (M2).

resource "aws_route53_zone" "triage" {
  name    = var.domain
  comment = "Delegated zone for the Nordwind triage console and API."

  tags = {
    c4_container = "console"
  }
}
