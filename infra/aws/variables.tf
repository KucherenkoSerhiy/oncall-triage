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
