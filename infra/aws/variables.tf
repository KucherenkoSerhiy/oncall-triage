variable "region" {
  description = "AWS region for every regional resource (Stockholm: inside the account's managed region floor)."
  type        = string
  default     = "eu-north-1"
}

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

variable "domain" {
  description = "Delegated DNS zone for the console and API."
  type        = string
  default     = "triage.serhiykucherenko.dev"
}

variable "parent_domain" {
  description = "Parent zone, hosted on Cloudflare, that delegates `var.domain` to Route 53."
  type        = string
  default     = "serhiykucherenko.dev"
}

variable "notification_email" {
  description = "Recipient of budget alerts."
  type        = string
  sensitive   = true
}

variable "monthly_budget_usd" {
  description = "AWS spend that triggers the budget alert."
  type        = number
  default     = 8
}

variable "worker_image_sha" {
  description = "Triage-worker image tag to deploy: `sha-<git sha>` from deploy.yml's `image` job, or an earlier one for rollback. Defaults to `latest` so a pull-request plan (no image job) is still realistic."
  type        = string
  default     = "latest"
}

variable "triage_model" {
  description = "LiteLLM model id the triage worker calls."
  type        = string
  default     = "anthropic/claude-haiku-4-5-20251001"
}

variable "daily_alert_cap" {
  description = "Maximum number of alerts triaged with a live model call per UTC day."
  type        = number
  default     = 500
}
