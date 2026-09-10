# M9a self-observability: a dashboard, five alarms into a human-only `ops`
# SNS topic (never the `alarms` topic - these alarms watch the triage brain
# itself, and feeding them back into ingest would have the brain triage
# itself), a daily `slo-reporter` Lambda, and the `CapReached` custom
# metric the triage worker emits (services/triage_worker/metrics.py).
#
# Cost: the dashboard is free (first one), and five ops alarms plus
# alarms.tf's six bank alarms puts the account at 11 CloudWatch alarms -
# one over the always-free 10. Combining two signals behind one alarm via
# metric math (an OR of two IF() expressions) would claw back inside the
# free tier, but at the cost of a genuinely ambiguous alarm name/reason on
# every page ("WorkerErrorsOrDuration" firing tells you nothing about
# which). Five separately-named, separately-actionable alarms are worth
# the ~$0.10/month for the 11th (docs/DESIGN.md section 9, "Cost model").

# ---------------------------------------------------------------- ops topic

# Deliberately NOT encrypted with the AWS-managed SNS key - the exact same
# trade-off, for the exact same reason, as the `alarms` topic (messaging.tf,
# #47): CloudWatch alarms cannot publish to a topic encrypted with
# `alias/aws/sns`, a CMK is ~$1/month for a payload with no customer data,
# and this topic is TLS-in-transit, publish-restricted to this account's
# CloudWatch alarms below.
resource "aws_sns_topic" "ops" {
  #checkov:skip=CKV_AWS_26:CloudWatch alarms cannot publish to topics encrypted with the AWS-managed SNS key; a CMK costs ~$1/month for a payload with no customer data (#47)
  name = "${local.name_prefix}-ops"

  tags = local.tags.ops
}

resource "aws_sns_topic_policy" "ops" {
  arn = aws_sns_topic.ops.arn
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "CloudWatchOpsAlarmsPublish"
      Effect    = "Allow"
      Principal = { Service = "cloudwatch.amazonaws.com" }
      Action    = "sns:Publish"
      Resource  = aws_sns_topic.ops.arn
      Condition = {
        StringEquals = { "aws:SourceAccount" = data.aws_caller_identity.current.account_id }
        ArnLike      = { "aws:SourceArn" = "arn:aws:cloudwatch:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:alarm:${local.name_prefix}-ops-*" }
      }
    }]
  })
}

# Human-only: no Lambda subscription. An operator reads these from their
# inbox (or the dashboard's alarm-status widget below), not the triage
# pipeline - see the comment at the top of this file.
resource "aws_sns_topic_subscription" "ops_email" {
  topic_arn = aws_sns_topic.ops.arn
  protocol  = "email"
  endpoint  = var.notification_email
}

# ---------------------------------------------------------------- ops alarms

resource "aws_cloudwatch_metric_alarm" "ops_ingest_error_ratio" {
  alarm_name          = "${local.name_prefix}-ops-IngestErrorRatio"
  alarm_description   = "ingest's error ratio (Errors / Invocations) is above 5% over 5 minutes."
  evaluation_periods  = 1
  threshold           = 0.05
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.ops.arn]
  ok_actions          = [aws_sns_topic.ops.arn]

  metric_query {
    id          = "errors"
    return_data = false
    metric {
      namespace   = "AWS/Lambda"
      metric_name = "Errors"
      dimensions  = { FunctionName = aws_lambda_function.ingest.function_name }
      period      = 300
      stat        = "Sum"
    }
  }

  metric_query {
    id          = "invocations"
    return_data = false
    metric {
      namespace   = "AWS/Lambda"
      metric_name = "Invocations"
      dimensions  = { FunctionName = aws_lambda_function.ingest.function_name }
      period      = 300
      stat        = "Sum"
    }
  }

  # Guards the divide against a silent quiet period (0 invocations would
  # otherwise be 0/0 = NaN, which CloudWatch treats as breaching).
  metric_query {
    id          = "ratio"
    expression  = "IF(invocations > 0, errors / invocations, 0)"
    label       = "IngestErrorRatio"
    return_data = true
  }

  tags = local.tags.ingest
}

resource "aws_cloudwatch_metric_alarm" "ops_worker_errors" {
  alarm_name          = "${local.name_prefix}-ops-WorkerErrors"
  alarm_description   = "the triage worker raised >= 3 errors over 15 minutes."
  namespace           = "AWS/Lambda"
  metric_name         = "Errors"
  dimensions          = { FunctionName = aws_lambda_function.triage_worker.function_name }
  statistic           = "Sum"
  period              = 900
  evaluation_periods  = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  threshold           = 3
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.ops.arn]
  ok_actions          = [aws_sns_topic.ops.arn]

  tags = local.tags.worker
}

resource "aws_cloudwatch_metric_alarm" "ops_alerts_dlq_depth" {
  alarm_name          = "${local.name_prefix}-ops-AlertsDlqDepth"
  alarm_description   = "the alerts DLQ has >= 1 message - a poison alert never got triaged."
  namespace           = "AWS/SQS"
  metric_name         = "ApproximateNumberOfMessagesVisible"
  dimensions          = { QueueName = aws_sqs_queue.alerts_dlq.name }
  statistic           = "Maximum"
  period              = 60
  evaluation_periods  = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  threshold           = 1
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.ops.arn]
  ok_actions          = [aws_sns_topic.ops.arn]

  tags = local.tags.queue
}

resource "aws_cloudwatch_metric_alarm" "ops_worker_duration_p95" {
  alarm_name          = "${local.name_prefix}-ops-WorkerDurationP95"
  alarm_description   = "the triage worker's p95 duration is above 60s over 5 minutes."
  namespace           = "AWS/Lambda"
  metric_name         = "Duration"
  dimensions          = { FunctionName = aws_lambda_function.triage_worker.function_name }
  extended_statistic  = "p95"
  period              = 300
  evaluation_periods  = 1
  comparison_operator = "GreaterThanThreshold"
  threshold           = 60000
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.ops.arn]
  ok_actions          = [aws_sns_topic.ops.arn]

  tags = local.tags.worker
}

resource "aws_cloudwatch_metric_alarm" "ops_cap_reached" {
  alarm_name          = "${local.name_prefix}-ops-CapReached"
  alarm_description   = "the daily LLM cap short-circuited >= 1 verdict over 5 minutes - traffic is outrunning var.daily_alert_cap."
  namespace           = "Nordwind/Triage"
  metric_name         = "CapReached"
  dimensions          = { estate = "all" }
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  threshold           = 1
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.ops.arn]
  ok_actions          = [aws_sns_topic.ops.arn]

  tags = local.tags.worker
}

locals {
  ops_alarm_names = [
    aws_cloudwatch_metric_alarm.ops_ingest_error_ratio.alarm_name,
    aws_cloudwatch_metric_alarm.ops_worker_errors.alarm_name,
    aws_cloudwatch_metric_alarm.ops_alerts_dlq_depth.alarm_name,
    aws_cloudwatch_metric_alarm.ops_worker_duration_p95.alarm_name,
    aws_cloudwatch_metric_alarm.ops_cap_reached.alarm_name,
  ]
  ops_alarm_arns = [
    aws_cloudwatch_metric_alarm.ops_ingest_error_ratio.arn,
    aws_cloudwatch_metric_alarm.ops_worker_errors.arn,
    aws_cloudwatch_metric_alarm.ops_alerts_dlq_depth.arn,
    aws_cloudwatch_metric_alarm.ops_worker_duration_p95.arn,
    aws_cloudwatch_metric_alarm.ops_cap_reached.arn,
  ]
}

output "ops_alarm_names" {
  description = "Names of the five human-only ops alarms (M9a)."
  value       = local.ops_alarm_names
}

# ---------------------------------------------------------------- slo-reporter

data "aws_iam_policy_document" "slo_reporter_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "slo_reporter" {
  name                 = "${var.project}-${var.environment}-slo-reporter"
  assume_role_policy   = data.aws_iam_policy_document.slo_reporter_assume.json
  permissions_boundary = local.workload_boundary_arn

  tags = local.tags.sloReporter
}

data "aws_iam_policy_document" "slo_reporter_inline" {
  statement {
    sid       = "ReadAlertsByStatus"
    actions   = ["dynamodb:Query"]
    resources = [aws_dynamodb_table.alerts.arn, "${aws_dynamodb_table.alerts.arn}/index/by_status"]
  }

  statement {
    sid       = "ReadVerdicts"
    actions   = ["dynamodb:GetItem"]
    resources = [aws_dynamodb_table.verdicts.arn]
  }

  statement {
    sid       = "EmitTriageMetrics"
    actions   = ["cloudwatch:PutMetricData"]
    resources = ["*"]

    condition {
      test     = "StringEquals"
      variable = "cloudwatch:namespace"
      values   = ["Nordwind/Triage"]
    }
  }
}

resource "aws_iam_role_policy" "slo_reporter" {
  name   = "${var.project}-${var.environment}-slo-reporter"
  role   = aws_iam_role.slo_reporter.id
  policy = data.aws_iam_policy_document.slo_reporter_inline.json
}

resource "aws_iam_role_policy_attachment" "slo_reporter_basic_execution" {
  role       = aws_iam_role.slo_reporter.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_cloudwatch_log_group" "slo_reporter" {
  name              = "/aws/lambda/${local.name_prefix}-slo-reporter"
  retention_in_days = 14

  tags = local.tags.sloReporter
}

resource "aws_lambda_function" "slo_reporter" {
  function_name = "${local.name_prefix}-slo-reporter"
  role          = aws_iam_role.slo_reporter.arn
  handler       = "bank.ops.slo_reporter.handler.lambda_handler"
  runtime       = "python3.12"
  architectures = ["arm64"]
  timeout       = 60
  memory_size   = 128

  filename         = data.archive_file.bank.output_path
  source_code_hash = data.archive_file.bank.output_base64sha256

  environment {
    variables = {
      ALERTS_TABLE   = aws_dynamodb_table.alerts.name
      VERDICTS_TABLE = aws_dynamodb_table.verdicts.name
      LOG_LEVEL      = "INFO"
    }
  }

  depends_on = [aws_cloudwatch_log_group.slo_reporter, aws_iam_role_policy.slo_reporter]

  tags = local.tags.sloReporter
}

resource "aws_cloudwatch_event_rule" "slo_reporter_schedule" {
  name                = "${local.name_prefix}-slo-reporter-schedule"
  description         = "Invokes slo-reporter once a day at 00:15 UTC to report on the previous UTC day."
  schedule_expression = "cron(15 0 * * ? *)"

  tags = local.tags.sloReporter
}

resource "aws_cloudwatch_event_target" "slo_reporter_schedule" {
  rule = aws_cloudwatch_event_rule.slo_reporter_schedule.name
  arn  = aws_lambda_function.slo_reporter.arn
}

resource "aws_lambda_permission" "slo_reporter_schedule" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.slo_reporter.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.slo_reporter_schedule.arn
}

# ---------------------------------------------------------------- dashboard

locals {
  dashboard_widgets = [
    {
      type   = "metric"
      x      = 0
      y      = 0
      width  = 12
      height = 6
      properties = {
        title  = "ingest"
        region = var.region
        view   = "timeSeries"
        stat   = "Sum"
        metrics = [
          ["AWS/Lambda", "Invocations", "FunctionName", aws_lambda_function.ingest.function_name],
          ["AWS/Lambda", "Errors", "FunctionName", aws_lambda_function.ingest.function_name],
          ["AWS/Lambda", "Duration", "FunctionName", aws_lambda_function.ingest.function_name, { stat = "p95" }],
        ]
      }
    },
    {
      type   = "metric"
      x      = 12
      y      = 0
      width  = 12
      height = 6
      properties = {
        title  = "alerts queue"
        region = var.region
        view   = "timeSeries"
        stat   = "Maximum"
        metrics = [
          ["AWS/SQS", "ApproximateNumberOfMessagesVisible", "QueueName", aws_sqs_queue.alerts.name],
          ["AWS/SQS", "ApproximateNumberOfMessagesVisible", "QueueName", aws_sqs_queue.alerts_dlq.name],
          ["AWS/SQS", "ApproximateAgeOfOldestMessage", "QueueName", aws_sqs_queue.alerts.name],
        ]
      }
    },
    {
      type   = "metric"
      x      = 0
      y      = 6
      width  = 12
      height = 6
      properties = {
        title  = "triage worker"
        region = var.region
        view   = "timeSeries"
        stat   = "Sum"
        metrics = [
          ["AWS/Lambda", "Invocations", "FunctionName", aws_lambda_function.triage_worker.function_name],
          ["AWS/Lambda", "Errors", "FunctionName", aws_lambda_function.triage_worker.function_name],
          ["AWS/Lambda", "Throttles", "FunctionName", aws_lambda_function.triage_worker.function_name],
          ["AWS/Lambda", "Duration", "FunctionName", aws_lambda_function.triage_worker.function_name, { stat = "p95" }],
        ]
      }
    },
    {
      type   = "metric"
      x      = 12
      y      = 6
      width  = 12
      height = 6
      properties = {
        title  = "API Gateway"
        region = var.region
        view   = "timeSeries"
        stat   = "Sum"
        metrics = [
          ["AWS/ApiGateway", "4xxError", "ApiId", aws_apigatewayv2_api.triage.id],
          ["AWS/ApiGateway", "5xxError", "ApiId", aws_apigatewayv2_api.triage.id],
          ["AWS/ApiGateway", "Latency", "ApiId", aws_apigatewayv2_api.triage.id, { stat = "p95" }],
        ]
      }
    },
    {
      type   = "metric"
      x      = 0
      y      = 12
      width  = 12
      height = 6
      properties = {
        title  = "bank estate (Nordwind/Bank)"
        region = var.region
        view   = "timeSeries"
        stat   = "Sum"
        metrics = [
          ["Nordwind/Bank", "PoolExhausted", "service", "payments"],
          ["Nordwind/Bank", "ReconciliationMismatch", "service", "ledger"],
          ["Nordwind/Bank", "AuthFailures", "service", "auth"],
          ["Nordwind/Bank", "AccountLockouts", "service", "auth"],
        ]
      }
    },
    {
      type   = "metric"
      x      = 12
      y      = 12
      width  = 12
      height = 6
      properties = {
        title  = "SLO (docs/slo.md)"
        region = var.region
        view   = "timeSeries"
        metrics = [
          ["Nordwind/Triage", "VerdictLatencyP95", "estate", "all", { stat = "Maximum", yAxis = "left" }],
          ["Nordwind/Triage", "SloAttainment", "estate", "all", { stat = "Average", yAxis = "right" }],
          ["Nordwind/Triage", "CapReached", "estate", "all", { stat = "Sum", yAxis = "left" }],
        ]
        annotations = {
          horizontal = [
            { label = "SLO target 95%", value = 0.95, yAxis = "right" },
          ]
        }
        yAxis = {
          right = { min = 0, max = 1 }
        }
      }
    },
    {
      type   = "alarm"
      x      = 0
      y      = 18
      width  = 24
      height = 6
      properties = {
        title  = "ops alarms"
        alarms = local.ops_alarm_arns
      }
    },
  ]
}

resource "aws_cloudwatch_dashboard" "triage" {
  dashboard_name = local.name_prefix
  dashboard_body = jsonencode({ widgets = local.dashboard_widgets })
}

output "dashboard_url" {
  description = "Console deep link to the self-observability dashboard."
  value       = "https://${var.region}.console.aws.amazon.com/cloudwatch/home?region=${var.region}#dashboards:name=${aws_cloudwatch_dashboard.triage.dashboard_name}"
}
