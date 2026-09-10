variable "github_owner" {
  description = "GitHub user or organization that owns the repository."
  type        = string
  default     = "KucherenkoSerhiy"
}

variable "github_repo" {
  description = "Repository name (without the owner) the environments belong to."
  type        = string
  default     = "oncall-triage"
}
