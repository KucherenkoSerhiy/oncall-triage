# The alerts queue decouples ingest from LLM latency; the DLQ catches
# poison messages after 3 failed attempts. The alarms topic fans CloudWatch
# alarm state changes (M4) into ingest via SNS -> Lambda.

resource "aws_sqs_queue" "alerts_dlq" {
  name                      = "${local.name_prefix}-alerts-dlq"
  message_retention_seconds = 1209600 # 14 days
  sqs_managed_sse_enabled   = true

  tags = local.tags.queue
}

resource "aws_sqs_queue" "alerts" {
  name                       = "${local.name_prefix}-alerts"
  visibility_timeout_seconds = 90
  sqs_managed_sse_enabled    = true

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.alerts_dlq.arn
    maxReceiveCount     = 3
  })

  tags = local.tags.queue
}

resource "aws_sqs_queue_redrive_allow_policy" "alerts_dlq" {
  queue_url = aws_sqs_queue.alerts_dlq.id

  redrive_allow_policy = jsonencode({
    redrivePermission = "byQueue"
    sourceQueueArns   = [aws_sqs_queue.alerts.arn]
  })
}

resource "aws_sns_topic" "alarms" {
  name              = "${local.name_prefix}-alarms"
  kms_master_key_id = "alias/aws/sns" # AWS-managed key: free, no extra KMS cost

  tags = local.tags.alarms
}

resource "aws_sns_topic_subscription" "alarms_to_ingest" {
  topic_arn = aws_sns_topic.alarms.arn
  protocol  = "lambda"
  endpoint  = aws_lambda_function.ingest.arn
}

resource "aws_lambda_permission" "alarms_invoke_ingest" {
  statement_id  = "AllowSNSAlarmsInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ingest.function_name
  principal     = "sns.amazonaws.com"
  source_arn    = aws_sns_topic.alarms.arn
}
