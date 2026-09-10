# Applied once by a human. Creates the two things GitHub Actions needs to
# do everything else without a stored credential: a state bucket and an
# OIDC-assumable deploy role.

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      project     = var.project
      env         = var.environment
      owner       = "serhiy"
      cost_center = "portfolio"
      managed_by  = "terraform/bootstrap"
    }
  }
}

data "aws_caller_identity" "current" {}

# ---------------------------------------------------------------- state bucket

resource "aws_s3_bucket" "tfstate" {
  bucket = var.state_bucket_name

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_s3_bucket_versioning" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "tfstate" {
  bucket                  = aws_s3_bucket.tfstate.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id

  rule {
    id     = "expire-old-state-versions"
    status = "Enabled"

    filter {}

    noncurrent_version_expiration {
      noncurrent_days = 90
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# ---------------------------------------------------------------- GitHub OIDC

resource "aws_iam_openid_connect_provider" "github" {
  url            = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"]
  # AWS validates GitHub's certificate chain against its own trust store
  # since 2023; the API still requires a thumbprint list, so these are the
  # published GitHub root CA thumbprints.
  thumbprint_list = [
    "6938fd4d98bab03faadb97b34396831e3780aea1",
    "1c58a3a8518e8759bf075b76b750d4f2df264fcd",
  ]
}

data "aws_iam_policy_document" "deploy_trust" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    # Plans from pull requests through the `plan` environment, applies from
    # the default branch through the `demo` environment, manual dispatches
    # from the default branch. GitHub emits either the classic subject
    # (repo:owner/repo:...) or, for newer repositories, the immutable one
    # (repo:owner@id/repo@id:...); both are accepted so a rename or an
    # ID-based token cannot lock the pipeline out. M9d: the bare
    # `pull_request` subject (any PR of this repository, unscoped) is
    # retired in favor of `environment:plan`, which only a PR run that
    # declares the `plan` environment can present - see ADR 0008.
    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values = flatten([
        for repo in [var.github_repository, var.github_repository_immutable] : [
          "repo:${repo}:ref:refs/heads/master",
          "repo:${repo}:ref:refs/heads/main",
          "repo:${repo}:environment:${var.environment}",
          "repo:${repo}:environment:${var.plan_environment}",
        ]
      ])
    }
  }
}

resource "aws_iam_role" "deploy" {
  name                 = "${var.project}-${var.environment}-github-deploy"
  assume_role_policy   = data.aws_iam_policy_document.deploy_trust.json
  max_session_duration = 3600
}

# The deploy role provisions the whole AWS root module. Actions are limited
# to the services the design uses; IAM is limited to roles and policies
# carrying the project prefix, plus PassRole to Lambda only.
data "aws_iam_policy_document" "deploy_permissions" {
  # The deploy role provisions the whole AWS root module, so service-wide
  # write actions are its job. It is assumable only by this repository via
  # OIDC, it is denied every iam:* action on its own identity, and every
  # role it creates must carry the workload permissions boundary.
  #checkov:skip=CKV_AWS_108:deploy role needs service-wide read on the services it provisions
  #checkov:skip=CKV_AWS_109:deploy role manages IAM only under the project prefix; self-edit denied
  #checkov:skip=CKV_AWS_110:privilege escalation closed by NeverEditOwnIdentity + CreateRoleRequiresBoundary
  #checkov:skip=CKV_AWS_111:deploy role needs service-wide write on the services it provisions
  #checkov:skip=CKV_AWS_290:same as CKV_AWS_111
  #checkov:skip=CKV_AWS_355:same as CKV_AWS_111
  #checkov:skip=CKV_AWS_356:same as CKV_AWS_111
  statement {
    sid = "StateBucket"
    actions = [
      "s3:ListBucket",
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
    ]
    resources = [
      aws_s3_bucket.tfstate.arn,
      "${aws_s3_bucket.tfstate.arn}/*",
    ]
  }

  statement {
    sid = "ProjectServices"
    actions = [
      "lambda:*",
      "dynamodb:*",
      "sqs:*",
      "sns:*",
      "apigateway:*",
      "s3:*",
      "cloudfront:*",
      "route53:*",
      "acm:*",
      "cloudwatch:*",
      "logs:*",
      "events:*",
      "ecr:*",
      "ssm:*",
      "budgets:*",
      "kms:Describe*",
      "kms:List*",
      # M9c: the DNSSEC signing key (asymmetric, us-east-1). Key *use* stays
      # with Route 53 via the key policy; the role only manages the key.
      "kms:CreateKey",
      "kms:CreateAlias",
      "kms:UpdateAlias",
      "kms:DeleteAlias",
      "kms:PutKeyPolicy",
      "kms:GetKeyPolicy",
      "kms:TagResource",
      "kms:UntagResource",
      "kms:UpdateKeyDescription",
      "kms:EnableKey",
      "kms:DisableKey",
      "kms:ScheduleKeyDeletion",
      "kms:CancelKeyDeletion",
      "kms:GetPublicKey",
      "sts:GetCallerIdentity",
    ]
    resources = ["*"]
  }

  statement {
    sid = "ProjectScopedIam"
    actions = [
      "iam:GetRole",
      "iam:CreateRole",
      "iam:DeleteRole",
      "iam:UpdateRole",
      "iam:TagRole",
      "iam:UntagRole",
      "iam:ListRolePolicies",
      "iam:ListAttachedRolePolicies",
      "iam:ListInstanceProfilesForRole",
      "iam:PutRolePolicy",
      "iam:DeleteRolePolicy",
      "iam:GetRolePolicy",
      "iam:AttachRolePolicy",
      "iam:DetachRolePolicy",
      "iam:CreatePolicy",
      "iam:DeletePolicy",
      "iam:GetPolicy",
      "iam:GetPolicyVersion",
      "iam:ListPolicyVersions",
      "iam:CreatePolicyVersion",
      "iam:DeletePolicyVersion",
      "iam:TagPolicy",
    ]
    resources = [
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.project}-*",
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:policy/${var.project}-*",
    ]
  }

  statement {
    sid     = "CreateRoleRequiresBoundary"
    effect  = "Deny"
    actions = ["iam:CreateRole"]
    resources = [
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.project}-*",
    ]

    condition {
      test     = "StringNotEquals"
      variable = "iam:PermissionsBoundary"
      values   = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:policy/${var.project}-${var.environment}-workload-boundary"]
    }
  }

  statement {
    sid     = "NeverEditOwnIdentity"
    effect  = "Deny"
    actions = ["iam:*"]
    resources = [
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.project}-${var.environment}-github-deploy",
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:policy/${var.project}-${var.environment}-github-deploy",
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:policy/${var.project}-${var.environment}-workload-boundary",
    ]
  }

  statement {
    sid       = "PassRoleToLambdaOnly"
    actions   = ["iam:PassRole"]
    resources = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.project}-*"]

    condition {
      test     = "StringEquals"
      variable = "iam:PassedToService"
      values   = ["lambda.amazonaws.com"]
    }
  }
}

# Roles the pipeline creates for workloads (Lambdas) must carry this
# boundary, so nothing the deploy role provisions can exceed it.
data "aws_iam_policy_document" "workload_boundary" {
  statement {
    sid     = "ProjectData"
    actions = ["dynamodb:*", "sqs:*", "sns:Publish", "lambda:InvokeFunction"]
    resources = [
      "arn:aws:dynamodb:${var.region}:${data.aws_caller_identity.current.account_id}:table/${var.project}-*",
      "arn:aws:sqs:${var.region}:${data.aws_caller_identity.current.account_id}:${var.project}-*",
      "arn:aws:sns:${var.region}:${data.aws_caller_identity.current.account_id}:${var.project}-*",
      "arn:aws:lambda:${var.region}:${data.aws_caller_identity.current.account_id}:function:${var.project}-*",
    ]
  }

  statement {
    sid       = "ProjectObjects"
    actions   = ["s3:GetObject", "s3:PutObject"]
    resources = ["arn:aws:s3:::${var.project}-*/*"]
  }

  statement {
    sid     = "ProjectSecrets"
    actions = ["ssm:GetParameter", "ssm:GetParameters", "kms:Decrypt"]
    resources = [
      "arn:aws:ssm:${var.region}:${data.aws_caller_identity.current.account_id}:parameter/${var.project}/*",
      "arn:aws:kms:${var.region}:${data.aws_caller_identity.current.account_id}:key/*",
    ]
  }

  statement {
    sid       = "ProjectLogs"
    actions   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["arn:aws:logs:${var.region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/${var.project}-*"]
  }

  # PutMetricData and the X-Ray write APIs accept no resource ARN.
  statement {
    sid       = "UnscopableTelemetry"
    actions   = ["cloudwatch:PutMetricData", "xray:PutTraceSegments", "xray:PutTelemetryRecords"]
    resources = ["*"]
  }
}

resource "aws_iam_policy" "workload_boundary" {
  name   = "${var.project}-${var.environment}-workload-boundary"
  policy = data.aws_iam_policy_document.workload_boundary.json
}

resource "aws_iam_policy" "deploy" {
  name   = "${var.project}-${var.environment}-github-deploy"
  policy = data.aws_iam_policy_document.deploy_permissions.json
}

resource "aws_iam_role_policy_attachment" "deploy" {
  role       = aws_iam_role.deploy.name
  policy_arn = aws_iam_policy.deploy.arn
}
