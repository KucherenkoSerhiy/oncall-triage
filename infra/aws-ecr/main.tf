provider "aws" {
  region = var.region

  default_tags {
    tags = {
      project     = var.project
      env         = var.environment
      owner       = "serhiy"
      cost_center = "portfolio"
      managed_by  = "terraform/aws-ecr"
    }
  }
}

locals {
  name_prefix = "${var.project}-${var.environment}"
}
