# The AWS bank estate (M4): payments, ledger, auth - three Lambdas with a
# shared fault control plane (bank-faults table) that `bankops chaos` and the
# console API's /chaos routes flip on and off. payments hands each synthetic
# authorisation to ledger over SQS; all three emit metrics that alarms.tf
# turns into CloudWatch alarms feeding the same SNS topic as the rest of the
# spine (messaging.tf).

resource "aws_dynamodb_table" "bank_faults" {
  name           = "${local.name_prefix}-bank-faults"
  billing_mode   = "PROVISIONED"
  read_capacity  = 1
  write_capacity = 1
  hash_key       = "service"

  attribute {
    name = "service"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = local.tags.faults
}

# ---------------------------------------------------------------- ledger queue

resource "aws_sqs_queue" "ledger_dlq" {
  name                      = "${local.name_prefix}-ledger-dlq"
  message_retention_seconds = 1209600 # 14 days
  sqs_managed_sse_enabled   = true

  tags = local.tags.ledgerQueue
}

resource "aws_sqs_queue" "ledger" {
  name                       = "${local.name_prefix}-ledger"
  visibility_timeout_seconds = 60
  sqs_managed_sse_enabled    = true

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.ledger_dlq.arn
    maxReceiveCount     = 5
  })

  tags = local.tags.ledgerQueue
}

resource "aws_sqs_queue_redrive_allow_policy" "ledger_dlq" {
  queue_url = aws_sqs_queue.ledger_dlq.id

  redrive_allow_policy = jsonencode({
    redrivePermission = "byQueue"
    sourceQueueArns   = [aws_sqs_queue.ledger.arn]
  })
}

# ---------------------------------------------------------------- packaging

# A separate zip from data.archive_file.services (lambdas.tf) so the bank
# Lambdas don't ship the ADK/triage-worker dependency tree they don't need.
# Handler dotted paths (bank.aws.payments.handler.lambda_handler etc.)
# require a top-level `bank` package in the zip, so - mirroring
# data.archive_file.services - the archive is built from the repo root with
# everything except `bank/` excluded.
data "archive_file" "bank" {
  type        = "zip"
  source_dir  = "${path.module}/../.."
  output_path = "${path.module}/build/bank.zip"

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
    "services",
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
    "**/__pycache__/**",
    "**/*.pyc",
    "**/.pytest_cache/**",
  ]
}

# ---------------------------------------------------------------- payments

data "aws_iam_policy_document" "payments_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "payments" {
  name                 = "${var.project}-${var.environment}-payments"
  assume_role_policy   = data.aws_iam_policy_document.payments_assume.json
  permissions_boundary = local.workload_boundary_arn

  tags = local.tags.payments
}

data "aws_iam_policy_document" "payments_inline" {
  statement {
    sid       = "ReadFaultFlag"
    actions   = ["dynamodb:GetItem"]
    resources = [aws_dynamodb_table.bank_faults.arn]
  }

  statement {
    sid       = "SendToLedgerQueue"
    actions   = ["sqs:SendMessage"]
    resources = [aws_sqs_queue.ledger.arn]
  }

  # PutMetricData accepts no resource ARN; scoped instead by the namespace
  # condition (see bootstrap/aws's workload boundary for the same trade-off).
  statement {
    sid       = "EmitBankMetrics"
    actions   = ["cloudwatch:PutMetricData"]
    resources = ["*"]

    condition {
      test     = "StringEquals"
      variable = "cloudwatch:namespace"
      values   = ["Nordwind/Bank"]
    }
  }
}

resource "aws_iam_role_policy" "payments" {
  name   = "${var.project}-${var.environment}-payments"
  role   = aws_iam_role.payments.id
  policy = data.aws_iam_policy_document.payments_inline.json
}

resource "aws_iam_role_policy_attachment" "payments_basic_execution" {
  role       = aws_iam_role.payments.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_cloudwatch_log_group" "payments" {
  name              = "/aws/lambda/${local.name_prefix}-payments"
  retention_in_days = 14

  tags = local.tags.payments
}

resource "aws_lambda_function" "payments" {
  function_name = "${local.name_prefix}-payments"
  role          = aws_iam_role.payments.arn
  handler       = "bank.aws.payments.handler.lambda_handler"
  runtime       = "python3.12"
  architectures = ["arm64"]
  timeout       = 10
  memory_size   = 128

  filename         = data.archive_file.bank.output_path
  source_code_hash = data.archive_file.bank.output_base64sha256

  environment {
    variables = {
      BANK_FAULTS_TABLE = aws_dynamodb_table.bank_faults.name
      LEDGER_QUEUE_URL  = aws_sqs_queue.ledger.id
    }
  }

  depends_on = [aws_cloudwatch_log_group.payments, aws_iam_role_policy.payments]

  tags = local.tags.payments
}

resource "aws_cloudwatch_event_rule" "payments_schedule" {
  name                = "${local.name_prefix}-payments-schedule"
  description         = "Invokes payments every minute to process a batch of synthetic authorisations."
  schedule_expression = "rate(1 minute)"

  tags = local.tags.payments
}

resource "aws_cloudwatch_event_target" "payments_schedule" {
  rule = aws_cloudwatch_event_rule.payments_schedule.name
  arn  = aws_lambda_function.payments.arn
}

resource "aws_lambda_permission" "payments_schedule" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.payments.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.payments_schedule.arn
}

# ---------------------------------------------------------------- ledger

data "aws_iam_policy_document" "ledger_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ledger" {
  name                 = "${var.project}-${var.environment}-ledger"
  assume_role_policy   = data.aws_iam_policy_document.ledger_assume.json
  permissions_boundary = local.workload_boundary_arn

  tags = local.tags.ledger
}

data "aws_iam_policy_document" "ledger_inline" {
  statement {
    sid       = "ReadFaultFlag"
    actions   = ["dynamodb:GetItem"]
    resources = [aws_dynamodb_table.bank_faults.arn]
  }

  statement {
    sid = "ConsumeLedgerQueue"
    actions = [
      "sqs:ReceiveMessage",
      "sqs:DeleteMessage",
      "sqs:GetQueueAttributes",
      "sqs:ChangeMessageVisibility",
    ]
    resources = [aws_sqs_queue.ledger.arn]
  }

  statement {
    sid       = "EmitBankMetrics"
    actions   = ["cloudwatch:PutMetricData"]
    resources = ["*"]

    condition {
      test     = "StringEquals"
      variable = "cloudwatch:namespace"
      values   = ["Nordwind/Bank"]
    }
  }
}

resource "aws_iam_role_policy" "ledger" {
  name   = "${var.project}-${var.environment}-ledger"
  role   = aws_iam_role.ledger.id
  policy = data.aws_iam_policy_document.ledger_inline.json
}

resource "aws_iam_role_policy_attachment" "ledger_basic_execution" {
  role       = aws_iam_role.ledger.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_cloudwatch_log_group" "ledger" {
  name              = "/aws/lambda/${local.name_prefix}-ledger"
  retention_in_days = 14

  tags = local.tags.ledger
}

resource "aws_lambda_function" "ledger" {
  function_name = "${local.name_prefix}-ledger"
  role          = aws_iam_role.ledger.arn
  handler       = "bank.aws.ledger.handler.lambda_handler"
  runtime       = "python3.12"
  architectures = ["arm64"]
  timeout       = 10
  memory_size   = 128

  filename         = data.archive_file.bank.output_path
  source_code_hash = data.archive_file.bank.output_base64sha256

  environment {
    variables = {
      BANK_FAULTS_TABLE = aws_dynamodb_table.bank_faults.name
    }
  }

  depends_on = [aws_cloudwatch_log_group.ledger, aws_iam_role_policy.ledger]

  tags = local.tags.ledger
}

resource "aws_lambda_event_source_mapping" "ledger" {
  event_source_arn = aws_sqs_queue.ledger.arn
  function_name    = aws_lambda_function.ledger.arn
  batch_size       = 5

  function_response_types = ["ReportBatchItemFailures"]
}

# ---------------------------------------------------------------- auth

data "aws_iam_policy_document" "auth_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "auth" {
  name                 = "${var.project}-${var.environment}-auth"
  assume_role_policy   = data.aws_iam_policy_document.auth_assume.json
  permissions_boundary = local.workload_boundary_arn

  tags = local.tags.auth
}

data "aws_iam_policy_document" "auth_inline" {
  statement {
    sid       = "ReadFaultFlag"
    actions   = ["dynamodb:GetItem"]
    resources = [aws_dynamodb_table.bank_faults.arn]
  }

  statement {
    sid       = "EmitBankMetrics"
    actions   = ["cloudwatch:PutMetricData"]
    resources = ["*"]

    condition {
      test     = "StringEquals"
      variable = "cloudwatch:namespace"
      values   = ["Nordwind/Bank"]
    }
  }
}

resource "aws_iam_role_policy" "auth" {
  name   = "${var.project}-${var.environment}-auth"
  role   = aws_iam_role.auth.id
  policy = data.aws_iam_policy_document.auth_inline.json
}

resource "aws_iam_role_policy_attachment" "auth_basic_execution" {
  role       = aws_iam_role.auth.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_cloudwatch_log_group" "auth" {
  name              = "/aws/lambda/${local.name_prefix}-auth"
  retention_in_days = 14

  tags = local.tags.auth
}

resource "aws_lambda_function" "auth" {
  function_name = "${local.name_prefix}-auth"
  role          = aws_iam_role.auth.arn
  handler       = "bank.aws.auth.handler.lambda_handler"
  runtime       = "python3.12"
  architectures = ["arm64"]
  timeout       = 10
  memory_size   = 128

  filename         = data.archive_file.bank.output_path
  source_code_hash = data.archive_file.bank.output_base64sha256

  environment {
    variables = {
      BANK_FAULTS_TABLE = aws_dynamodb_table.bank_faults.name
    }
  }

  depends_on = [aws_cloudwatch_log_group.auth, aws_iam_role_policy.auth]

  tags = local.tags.auth
}

resource "aws_cloudwatch_event_rule" "auth_schedule" {
  name                = "${local.name_prefix}-auth-schedule"
  description         = "Invokes auth every minute to process a batch of synthetic token issuances."
  schedule_expression = "rate(1 minute)"

  tags = local.tags.auth
}

resource "aws_cloudwatch_event_target" "auth_schedule" {
  rule = aws_cloudwatch_event_rule.auth_schedule.name
  arn  = aws_lambda_function.auth.arn
}

resource "aws_lambda_permission" "auth_schedule" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.auth.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.auth_schedule.arn
}

# ---------------------------------------------------------------- console-api chaos routes

data "aws_iam_policy_document" "console_api_chaos" {
  statement {
    sid       = "BankFaultsControlPlane"
    actions   = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:DeleteItem", "dynamodb:Scan"]
    resources = [aws_dynamodb_table.bank_faults.arn]
  }
}

resource "aws_iam_role_policy" "console_api_chaos" {
  name   = "${var.project}-${var.environment}-console-api-chaos"
  role   = aws_iam_role.console_api.id
  policy = data.aws_iam_policy_document.console_api_chaos.json
}
