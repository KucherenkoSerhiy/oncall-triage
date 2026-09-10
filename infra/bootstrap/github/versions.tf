terraform {
  required_version = ">= 1.10"

  required_providers {
    github = {
      source  = "integrations/github"
      version = ">= 6.0, < 7.0"
    }
  }

  # Same bucket infra/bootstrap/aws creates, under its own key - see
  # infra/README.md "Bootstrap" for the -backend-config flags.
  backend "s3" {
    key          = "bootstrap/github.tfstate"
    encrypt      = true
    use_lockfile = true
  }
}
