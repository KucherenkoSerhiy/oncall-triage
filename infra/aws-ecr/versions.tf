terraform {
  required_version = ">= 1.10"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.90, < 7.0"
    }
  }

  # bucket and region arrive via -backend-config from deploy.yml
  # (repository variable TF_STATE_BUCKET); the key is fixed per root.
  # Same state bucket as infra/aws, separate key - see infra/README.md for
  # why the ECR repository has its own tiny root (apply ordering).
  backend "s3" {
    key          = "aws-ecr/terraform.tfstate"
    encrypt      = true
    use_lockfile = true
  }
}
