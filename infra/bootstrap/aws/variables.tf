variable "region" {
  description = "Home region for the state bucket and the deploy role (the account's managed region floor allows eu-north-1 plus global services)."
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

variable "github_repository" {
  description = "owner/repo allowed to assume the deploy role via OIDC."
  type        = string
  default     = "KucherenkoSerhiy/oncall-triage"
}

variable "github_repository_immutable" {
  description = "owner@ownerId/repo@repoId - the immutable subject form newer repositories emit in OIDC tokens (GET /repos/{owner}/{repo}/actions/oidc/customization/sub)."
  type        = string
  default     = "KucherenkoSerhiy@13918875/oncall-triage@1360265871"
}

variable "state_bucket_name" {
  description = "Globally unique name for the Terraform state bucket."
  type        = string
  default     = "nordwind-triage-tfstate-eu-north-1"
}
