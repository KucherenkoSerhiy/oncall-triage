variable "location" {
  description = "Azure region for the resource group."
  type        = string
  default     = "westeurope"
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
  description = "owner/repo allowed to use the federated credentials."
  type        = string
  default     = "KucherenkoSerhiy/oncall-triage"
}
