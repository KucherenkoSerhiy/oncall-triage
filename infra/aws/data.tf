# Account, region and the workload permissions boundary applied to every
# role this root creates (bootstrap/aws denies iam:CreateRole without it).

data "aws_caller_identity" "current" {}

data "aws_region" "current" {}

# The workload permissions boundary is created by infra/bootstrap/aws with a
# deterministic name. Its ARN is composed here rather than looked up with
# `data "aws_iam_policy"`, because that lookup needs the account-wide
# iam:ListPolicies permission the deploy role deliberately does not have.
locals {
  workload_boundary_arn = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:policy/${var.project}-${var.environment}-workload-boundary"
}

# The repository itself lives in infra/aws-ecr (applied first by deploy.yml's
# `ecr` job) so a fresh account doesn't need the Lambda image to exist before
# the repository that would hold it does. See infra/README.md.
data "aws_ecr_repository" "triage_worker" {
  name = "${local.name_prefix}-triage-worker"
}
