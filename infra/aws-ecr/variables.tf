variable "region" {
  description = "AWS region for the repository (must match infra/aws)."
  type        = string
  default     = "eu-north-1"
}

variable "project" {
  description = "Project slug used in names and tags (must match infra/aws)."
  type        = string
  default     = "nordwind-triage"
}

variable "environment" {
  description = "Environment slug used in names and tags (must match infra/aws)."
  type        = string
  default     = "demo"
}
