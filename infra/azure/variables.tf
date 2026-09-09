variable "project" {
  description = "Project slug used in names and tags."
  type        = string
  default     = "nordwind-triage"
}

variable "environment" {
  description = "Environment slug used in names and tags."
  type        = string
  default     = "demo"
}

variable "notification_email" {
  description = "Recipient of budget alerts."
  type        = string
  sensitive   = true
}

variable "monthly_budget_usd" {
  description = "Azure spend that triggers the budget alert."
  type        = number
  default     = 2
}

# Read from AWS SSM by deploy.yml with the AWS role (infra/aws already owns
# and generates these two secrets) and passed as -var flags - infra/azure
# never talks to AWS itself, so it cannot read them back on its own. See
# infra/README.md for the plaintext-app-settings trade-off this implies.
variable "console_token" {
  description = "Bearer token for customer-notifications' chaos poll (same value as AWS's console-token SSM parameter)."
  type        = string
  sensitive   = true
}

variable "ingest_hmac_secret" {
  description = "HMAC secret the alert forwarder signs with (same value as AWS's ingest-hmac-secret SSM parameter)."
  type        = string
  sensitive   = true
}
