# Packaging: one zip shared by the two remaining zip-packaged functions,
# ingest and console-api (the triage worker moved to an image-based Lambda
# in M3b - see the triage-worker section below). The handler dotted paths
# (services.ingest.handler.lambda_handler etc.) require a top-level
# `services` package in the zip, so the archive is built from the repo
# root with everything except `services/` excluded - `cli/` included,
# since it is a sibling of `services/` at the repo root and is not needed
# by any Lambda.
data "archive_file" "services" {
  type        = "zip"
  source_dir  = "${path.module}/../.."
  output_path = "${path.module}/build/services.zip"

  excludes = [
    ".git",
    ".github",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "cli",
    "docs",
    "infra",
    "node_modules",
    "oncall_triage",
    "scripts",
    "tests",
    ".checkov.yaml",
    ".editorconfig",
    ".env.example",
    ".pre-commit-config.yaml",
    ".tflint.hcl",
    "ARCHITECTURE.md",
    "DEMO.md",
    "LICENSE",
    "README.md",
    "SPEC.md",
    "Taskfile.yml",
    "console",
    "demo.sh",
    "known_issues.json",
    "pyproject.toml",
    "requirements-dev.txt",
    "requirements.txt",
    "services/ingest/README.md",
    "**/__pycache__/**",
    "**/*.pyc",
    "**/.pytest_cache/**",
  ]
}

# Read back at deploy time: values are generated in secrets.tf so no
# plaintext ever lands in the repo, but they do end up as plaintext in
# each Lambda's environment configuration (visible to anyone who can call
# lambda:GetFunctionConfiguration). Accepted v1 trade-off; SSM stays the
# source of truth and the operator-facing parameter for `bankops`.
data "aws_ssm_parameter" "ingest_hmac_secret" {
  name            = aws_ssm_parameter.ingest_hmac_secret.name
  with_decryption = true
}

data "aws_ssm_parameter" "console_token" {
  name            = aws_ssm_parameter.console_token.name
  with_decryption = true
}

# Not created by Terraform - its value is a human secret, set once (and
# rotated) by the operator command in infra/README.md, or via deploy.yml's
# manual `anthropic_api_key` dispatch input. See the precondition on
# aws_lambda_function.triage_worker below for what happens if it is missing.
data "aws_ssm_parameter" "anthropic_api_key" {
  name            = "/${var.project}/${var.environment}/anthropic-api-key"
  with_decryption = true
}

# ---------------------------------------------------------------- log groups

resource "aws_cloudwatch_log_group" "ingest" {
  name              = "/aws/lambda/${local.name_prefix}-ingest"
  retention_in_days = 14

  tags = local.tags.ingest
}

resource "aws_cloudwatch_log_group" "console_api" {
  name              = "/aws/lambda/${local.name_prefix}-console-api"
  retention_in_days = 14

  tags = local.tags.api
}

resource "aws_cloudwatch_log_group" "triage_worker" {
  name              = "/aws/lambda/${local.name_prefix}-triage-worker"
  retention_in_days = 14

  tags = local.tags.worker
}

# ---------------------------------------------------------------- ingest

data "aws_iam_policy_document" "ingest_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ingest" {
  name                 = "${var.project}-${var.environment}-ingest"
  assume_role_policy   = data.aws_iam_policy_document.ingest_assume.json
  permissions_boundary = local.workload_boundary_arn

  tags = local.tags.ingest
}

data "aws_iam_policy_document" "ingest_inline" {
  statement {
    sid       = "AlertsTable"
    actions   = ["dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:Query"]
    resources = [aws_dynamodb_table.alerts.arn, "${aws_dynamodb_table.alerts.arn}/index/*"]
  }

  statement {
    sid       = "SendToQueue"
    actions   = ["sqs:SendMessage"]
    resources = [aws_sqs_queue.alerts.arn]
  }

  statement {
    sid       = "ReadHmacSecret"
    actions   = ["ssm:GetParameter"]
    resources = [aws_ssm_parameter.ingest_hmac_secret.arn]
  }
}

resource "aws_iam_role_policy" "ingest" {
  name   = "${var.project}-${var.environment}-ingest"
  role   = aws_iam_role.ingest.id
  policy = data.aws_iam_policy_document.ingest_inline.json
}

resource "aws_iam_role_policy_attachment" "ingest_basic_execution" {
  role       = aws_iam_role.ingest.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_lambda_function" "ingest" {
  function_name = "${local.name_prefix}-ingest"
  role          = aws_iam_role.ingest.arn
  handler       = "services.ingest.handler.lambda_handler"
  runtime       = "python3.12"
  architectures = ["arm64"]
  timeout       = 30
  memory_size   = 256

  filename         = data.archive_file.services.output_path
  source_code_hash = data.archive_file.services.output_base64sha256

  environment {
    variables = {
      ALERTS_TABLE       = aws_dynamodb_table.alerts.name
      ALERTS_QUEUE_URL   = aws_sqs_queue.alerts.id
      INGEST_HMAC_SECRET = data.aws_ssm_parameter.ingest_hmac_secret.value
    }
  }

  depends_on = [aws_cloudwatch_log_group.ingest, aws_iam_role_policy.ingest]

  tags = local.tags.ingest
}

# ---------------------------------------------------------------- console-api

data "aws_iam_policy_document" "console_api_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "console_api" {
  name                 = "${var.project}-${var.environment}-console-api"
  assume_role_policy   = data.aws_iam_policy_document.console_api_assume.json
  permissions_boundary = local.workload_boundary_arn

  tags = local.tags.api
}

data "aws_iam_policy_document" "console_api_inline" {
  statement {
    sid     = "AlertsAndVerdicts"
    actions = ["dynamodb:Query", "dynamodb:GetItem"]
    resources = [
      aws_dynamodb_table.alerts.arn,
      "${aws_dynamodb_table.alerts.arn}/index/*",
      aws_dynamodb_table.verdicts.arn,
    ]
  }

  statement {
    sid       = "KnownIssues"
    actions   = ["dynamodb:Query", "dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:DeleteItem"]
    resources = [aws_dynamodb_table.known_issues.arn]
  }

  statement {
    sid       = "ReadConsoleToken"
    actions   = ["ssm:GetParameter"]
    resources = [aws_ssm_parameter.console_token.arn]
  }
}

resource "aws_iam_role_policy" "console_api" {
  name   = "${var.project}-${var.environment}-console-api"
  role   = aws_iam_role.console_api.id
  policy = data.aws_iam_policy_document.console_api_inline.json
}

resource "aws_iam_role_policy_attachment" "console_api_basic_execution" {
  role       = aws_iam_role.console_api.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_lambda_function" "console_api" {
  function_name = "${local.name_prefix}-console-api"
  role          = aws_iam_role.console_api.arn
  handler       = "services.console_api.handler.lambda_handler"
  runtime       = "python3.12"
  architectures = ["arm64"]
  timeout       = 30
  memory_size   = 256

  filename         = data.archive_file.services.output_path
  source_code_hash = data.archive_file.services.output_base64sha256

  environment {
    variables = {
      ALERTS_TABLE       = aws_dynamodb_table.alerts.name
      VERDICTS_TABLE     = aws_dynamodb_table.verdicts.name
      KNOWN_ISSUES_TABLE = aws_dynamodb_table.known_issues.name
      CONSOLE_TOKEN      = data.aws_ssm_parameter.console_token.value
      CONSOLE_ORIGIN     = local.console_origin
    }
  }

  depends_on = [aws_cloudwatch_log_group.console_api, aws_iam_role_policy.console_api]

  tags = local.tags.api
}

# ---------------------------------------------------------------- triage-worker

data "aws_iam_policy_document" "triage_worker_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "triage_worker" {
  name                 = "${var.project}-${var.environment}-triage-worker"
  assume_role_policy   = data.aws_iam_policy_document.triage_worker_assume.json
  permissions_boundary = local.workload_boundary_arn

  tags = local.tags.worker
}

data "aws_iam_policy_document" "triage_worker_inline" {
  statement {
    sid       = "AlertsTable"
    actions   = ["dynamodb:GetItem", "dynamodb:UpdateItem", "dynamodb:Query"]
    resources = [aws_dynamodb_table.alerts.arn, "${aws_dynamodb_table.alerts.arn}/index/by_status"]
  }

  # GetItem backs the redelivery short-circuit in handler.py; PutItem writes
  # the verdict; UpdateItem is the atomic daily-cap counter (cap.py).
  statement {
    sid       = "VerdictsTable"
    actions   = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem"]
    resources = [aws_dynamodb_table.verdicts.arn]
  }

  statement {
    sid       = "KnownIssuesTable"
    actions   = ["dynamodb:Query", "dynamodb:PutItem"]
    resources = [aws_dynamodb_table.known_issues.arn]
  }

  statement {
    sid = "ConsumeQueue"
    actions = [
      "sqs:ReceiveMessage",
      "sqs:DeleteMessage",
      "sqs:GetQueueAttributes",
      "sqs:ChangeMessageVisibility",
    ]
    resources = [aws_sqs_queue.alerts.arn]
  }
}

resource "aws_iam_role_policy" "triage_worker" {
  name   = "${var.project}-${var.environment}-triage-worker"
  role   = aws_iam_role.triage_worker.id
  policy = data.aws_iam_policy_document.triage_worker_inline.json
}

resource "aws_iam_role_policy_attachment" "triage_worker_basic_execution" {
  role       = aws_iam_role.triage_worker.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_lambda_function" "triage_worker" {
  function_name = "${local.name_prefix}-triage-worker"
  role          = aws_iam_role.triage_worker.arn
  package_type  = "Image"
  image_uri     = "${data.aws_ecr_repository.triage_worker.repository_url}:${var.worker_image_sha}"
  architectures = ["arm64"]
  timeout       = 120
  memory_size   = 1024

  environment {
    variables = {
      ALERTS_TABLE       = aws_dynamodb_table.alerts.name
      VERDICTS_TABLE     = aws_dynamodb_table.verdicts.name
      KNOWN_ISSUES_TABLE = aws_dynamodb_table.known_issues.name
      ANTHROPIC_API_KEY  = data.aws_ssm_parameter.anthropic_api_key.value
      TRIAGE_MODEL       = var.triage_model
      DAILY_ALERT_CAP    = tostring(var.daily_alert_cap)
      LOG_LEVEL          = "INFO"
    }
  }

  depends_on = [aws_cloudwatch_log_group.triage_worker, aws_iam_role_policy.triage_worker]

  lifecycle {
    precondition {
      condition     = data.aws_ssm_parameter.anthropic_api_key.value != ""
      error_message = "SSM parameter /${var.project}/${var.environment}/anthropic-api-key is empty or missing. Create it once with: aws ssm put-parameter --name /${var.project}/${var.environment}/anthropic-api-key --type SecureString --value <key> --overwrite (or run deploy.yml's workflow_dispatch with the anthropic_api_key input)."
    }
  }

  tags = local.tags.worker
}

resource "aws_lambda_event_source_mapping" "triage_worker" {
  event_source_arn = aws_sqs_queue.alerts.arn
  function_name    = aws_lambda_function.triage_worker.arn
  batch_size       = 5

  function_response_types = ["ReportBatchItemFailures"]
}
