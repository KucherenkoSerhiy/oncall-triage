# M9b backups: a weekly JSON export of the known-issues table to a private
# S3 bucket, so the taught memory an operator has spent weeks building
# survives a table wipe (`bankops known-issues import` is the restore path -
# see infra/README.md "Backups"). observability.tf is already close to the
# ~400-line guideline from docs/specs/m9b-known-issues-export-and-dlq.md, so
# this lives in its own file.

# ---------------------------------------------------------------- bucket

resource "aws_s3_bucket" "known_issues" {
  #checkov:skip=CKV_AWS_21:versioning stays off on purpose - see the lifecycle rule below (disposable weekly snapshots, not a served site)
  bucket = "${local.name_prefix}-known-issues-${data.aws_caller_identity.current.account_id}"

  tags = local.tags.knownIssuesBucket
}

resource "aws_s3_bucket_server_side_encryption_configuration" "known_issues" {
  bucket = aws_s3_bucket.known_issues.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "known_issues" {
  bucket                  = aws_s3_bucket.known_issues.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Versioning stays off (unlike the console bucket): these are disposable
# weekly snapshots, not a served site whose previous versions matter. Access
# logging, cross-region replication and a CMK are the same free-tier
# trade-offs already made for the Terraform state bucket - skipped repo-wide
# with reasons in .checkov.yaml (CKV_AWS_18 / CKV_AWS_144 / CKV2_AWS_62 /
# CKV_AWS_145) rather than repeated per bucket.
resource "aws_s3_bucket_lifecycle_configuration" "known_issues" {
  bucket = aws_s3_bucket.known_issues.id

  rule {
    id     = "expire-exports"
    status = "Enabled"

    filter {}

    expiration {
      days = 30
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# ---------------------------------------------------------------- known-issues-export

data "aws_iam_policy_document" "known_issues_export_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "known_issues_export" {
  name                 = "${var.project}-${var.environment}-known-issues-export"
  assume_role_policy   = data.aws_iam_policy_document.known_issues_export_assume.json
  permissions_boundary = local.workload_boundary_arn

  tags = local.tags.knownIssuesExport
}

data "aws_iam_policy_document" "known_issues_export_inline" {
  statement {
    sid       = "ScanKnownIssues"
    actions   = ["dynamodb:Scan"]
    resources = [aws_dynamodb_table.known_issues.arn]
  }

  statement {
    sid       = "PutExportObject"
    actions   = ["s3:PutObject"]
    resources = ["${aws_s3_bucket.known_issues.arn}/known-issues-*.json"]
  }
}

resource "aws_iam_role_policy" "known_issues_export" {
  name   = "${var.project}-${var.environment}-known-issues-export"
  role   = aws_iam_role.known_issues_export.id
  policy = data.aws_iam_policy_document.known_issues_export_inline.json
}

resource "aws_iam_role_policy_attachment" "known_issues_export_basic_execution" {
  role       = aws_iam_role.known_issues_export.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_cloudwatch_log_group" "known_issues_export" {
  name              = "/aws/lambda/${local.name_prefix}-known-issues-export"
  retention_in_days = 14

  tags = local.tags.knownIssuesExport
}

resource "aws_lambda_function" "known_issues_export" {
  function_name = "${local.name_prefix}-known-issues-export"
  role          = aws_iam_role.known_issues_export.arn
  handler       = "bank.ops.known_issues_export.handler.lambda_handler"
  runtime       = "python3.12"
  architectures = ["arm64"]
  timeout       = 60
  memory_size   = 128

  filename         = data.archive_file.bank.output_path
  source_code_hash = data.archive_file.bank.output_base64sha256

  environment {
    variables = {
      KNOWN_ISSUES_TABLE  = aws_dynamodb_table.known_issues.name
      KNOWN_ISSUES_BUCKET = aws_s3_bucket.known_issues.id
      LOG_LEVEL           = "INFO"
    }
  }

  depends_on = [aws_cloudwatch_log_group.known_issues_export, aws_iam_role_policy.known_issues_export]

  tags = local.tags.knownIssuesExport
}

resource "aws_cloudwatch_event_rule" "known_issues_export_schedule" {
  name                = "${local.name_prefix}-known-issues-export-schedule"
  description         = "Invokes known-issues-export every Monday at 00:30 UTC."
  schedule_expression = "cron(30 0 ? * MON *)"

  tags = local.tags.knownIssuesExport
}

resource "aws_cloudwatch_event_target" "known_issues_export_schedule" {
  rule = aws_cloudwatch_event_rule.known_issues_export_schedule.name
  arn  = aws_lambda_function.known_issues_export.arn
}

resource "aws_lambda_permission" "known_issues_export_schedule" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.known_issues_export.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.known_issues_export_schedule.arn
}

output "known_issues_bucket" {
  description = "Private S3 bucket holding weekly known-issues JSON exports (M9b)."
  value       = aws_s3_bucket.known_issues.id
}
