# CloudWatch alarms for the AWS bank estate (M4). Every alarm publishes to
# the same SNS topic the ingest Lambda already subscribes to (messaging.tf);
# `services/ingest/adapters/cloudwatch.py` parses `AlarmDescription`'s
# `service=<name>` and the `SevN` suffix on the alarm name. Six alarms, four
# custom metrics (PoolExhausted, ReconciliationMismatch, AuthFailures,
# AccountLockouts) - within the always-free budget (<= 6 alarms, <= 4 custom
# metrics; the built-in Lambda/SQS metrics below don't count against it).

resource "aws_cloudwatch_metric_alarm" "payments_errors" {
  alarm_name          = "${local.name_prefix}-payments-Errors-Sev2"
  alarm_description   = "service=payments; the payments Lambda is raising errors (errors fault or a real upstream issue)."
  namespace           = "AWS/Lambda"
  metric_name         = "Errors"
  dimensions          = { FunctionName = aws_lambda_function.payments.function_name }
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  threshold           = 3
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alarms.arn]

  tags = local.tags.payments
}

resource "aws_cloudwatch_metric_alarm" "payments_duration" {
  alarm_name          = "${local.name_prefix}-payments-Duration-Sev3"
  alarm_description   = "service=payments; payments p99 latency is above 2s (latency fault or a real slowdown)."
  namespace           = "AWS/Lambda"
  metric_name         = "Duration"
  dimensions          = { FunctionName = aws_lambda_function.payments.function_name }
  extended_statistic  = "p99"
  period              = 300
  evaluation_periods  = 1
  comparison_operator = "GreaterThanThreshold"
  threshold           = 2000
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alarms.arn]

  tags = local.tags.payments
}

resource "aws_cloudwatch_metric_alarm" "payments_pool_exhausted" {
  alarm_name          = "${local.name_prefix}-payments-PoolExhausted-Sev3"
  alarm_description   = "service=payments; connection pool exhausted while authorizing payments - known scaling limit, auto-recovers."
  namespace           = "Nordwind/Bank"
  metric_name         = "PoolExhausted"
  dimensions          = { service = "payments" }
  statistic           = "Sum"
  period              = 60
  evaluation_periods  = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  threshold           = 1
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alarms.arn]

  tags = local.tags.payments
}

resource "aws_cloudwatch_metric_alarm" "ledger_queue_age" {
  alarm_name          = "${local.name_prefix}-ledger-ApproximateAgeOfOldestMessage-Sev2"
  alarm_description   = "service=ledger; the ledger queue's oldest message has been waiting more than 5 minutes (lag fault or a real backlog)."
  namespace           = "AWS/SQS"
  metric_name         = "ApproximateAgeOfOldestMessage"
  dimensions          = { QueueName = aws_sqs_queue.ledger.name }
  statistic           = "Maximum"
  period              = 300
  evaluation_periods  = 1
  comparison_operator = "GreaterThanThreshold"
  threshold           = 300
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alarms.arn]

  tags = local.tags.ledger
}

resource "aws_cloudwatch_metric_alarm" "ledger_reconciliation_mismatch" {
  alarm_name          = "${local.name_prefix}-ledger-ReconciliationMismatch-Sev1"
  alarm_description   = "service=ledger; a ledger reconciliation mismatch was detected."
  namespace           = "Nordwind/Bank"
  metric_name         = "ReconciliationMismatch"
  dimensions          = { service = "ledger" }
  statistic           = "Sum"
  period              = 60
  evaluation_periods  = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  threshold           = 1
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alarms.arn]

  tags = local.tags.ledger
}

resource "aws_cloudwatch_metric_alarm" "auth_failures" {
  alarm_name          = "${local.name_prefix}-auth-AuthFailures-Sev2"
  alarm_description   = "service=auth; a burst of token verification failures (jwks-rotation fault or a real key rotation gone wrong)."
  namespace           = "Nordwind/Bank"
  metric_name         = "AuthFailures"
  dimensions          = { service = "auth" }
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  threshold           = 15
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alarms.arn]

  tags = local.tags.auth
}

output "alarm_names" {
  description = "Names of every CloudWatch alarm feeding the alarms SNS topic (bank estate, M4)."
  value = [
    aws_cloudwatch_metric_alarm.payments_errors.alarm_name,
    aws_cloudwatch_metric_alarm.payments_duration.alarm_name,
    aws_cloudwatch_metric_alarm.payments_pool_exhausted.alarm_name,
    aws_cloudwatch_metric_alarm.ledger_queue_age.alarm_name,
    aws_cloudwatch_metric_alarm.ledger_reconciliation_mismatch.alarm_name,
    aws_cloudwatch_metric_alarm.auth_failures.alarm_name,
  ]
}
