terraform {
  required_version = ">= 1.10"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.90, < 7.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = ">= 2.4, < 3.0"
    }
    random = {
      source  = "hashicorp/random"
      version = ">= 3.6, < 4.0"
    }
  }

  # bucket and region arrive via -backend-config from deploy.yml
  # (repository variable TF_STATE_BUCKET); the key is fixed per root.
  backend "s3" {
    key          = "aws/terraform.tfstate"
    encrypt      = true
    use_lockfile = true
  }
}
