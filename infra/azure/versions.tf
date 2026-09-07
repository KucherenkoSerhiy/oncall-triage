terraform {
  required_version = ">= 1.10"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">= 4.0, < 5.0"
    }
  }

  # Same S3 backend as the AWS root (one place for all state); Azure auth
  # is OIDC via ARM_* environment variables set by deploy.yml.
  backend "s3" {
    key          = "azure/terraform.tfstate"
    encrypt      = true
    use_lockfile = true
  }
}
