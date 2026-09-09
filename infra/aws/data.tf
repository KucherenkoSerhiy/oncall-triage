# Account, region and the workload permissions boundary applied to every
# role this root creates (bootstrap/aws denies iam:CreateRole without it).

data "aws_caller_identity" "current" {}

data "aws_region" "current" {}

data "aws_iam_policy" "workload_boundary" {
  name = "${var.project}-${var.environment}-workload-boundary"
}
