variable "region" {
  description = "Home region for the state bucket and the deploy role."
  type        = string
  default     = "eu-central-1"
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

variable "github_repository" {
  description = "owner/repo allowed to assume the deploy role via OIDC."
  type        = string
  default     = "KucherenkoSerhiy/oncall-triage"
}

variable "state_bucket_name" {
  description = "Globally unique name for the Terraform state bucket."
  type        = string
  default     = "nordwind-triage-tfstate-eu-central-1"
}
