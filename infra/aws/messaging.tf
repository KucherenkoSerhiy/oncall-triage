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
  name = "${local.name_prefix}-alerts"
  # >= 6x the triage-worker timeout (120 s, lambdas.tf), per the Lambda/SQS
  # guidance: a slow verdict must not be redelivered while still in flight
  # (#39). Redelivery of a genuinely failed batch item therefore waits up to
  # 12 min, which the console shows as "queued" - acceptable for triage.
  visibility_timeout_seconds = 720
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

# Deliberately NOT encrypted with the AWS-managed SNS key: CloudWatch alarms
# cannot publish to a topic encrypted with `alias/aws/sns` (its key policy
# does not grant cloudwatch.amazonaws.com), which silently dropped every
# alarm notification in M4's first live probe (#47). A customer-managed key
# would fix it for ~$1/month; alarm state changes carry no customer data,
# transit is TLS, and the topic accepts publishes only from this account's
# CloudWatch (policy below) - so the always-free option is the right trade.
resource "aws_sns_topic" "alarms" {
  #checkov:skip=CKV_AWS_26:CloudWatch alarms cannot publish to topics encrypted with the AWS-managed SNS key; a CMK costs ~$1/month for a payload with no customer data (#47)
  name = "${local.name_prefix}-alarms"

  tags = local.tags.alarms
}

resource "aws_sns_topic_policy" "alarms" {
  arn = aws_sns_topic.alarms.arn
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "CloudWatchAlarmsPublish"
      Effect    = "Allow"
      Principal = { Service = "cloudwatch.amazonaws.com" }
      Action    = "sns:Publish"
      Resource  = aws_sns_topic.alarms.arn
      Condition = {
        StringEquals = { "aws:SourceAccount" = data.aws_caller_identity.current.account_id }
        ArnLike      = { "aws:SourceArn" = "arn:aws:cloudwatch:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:alarm:${local.name_prefix}-*" }
      }
    }]
  })
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
