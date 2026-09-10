output "name_servers" {
  description = "Route 53 name servers of the delegated zone (written to the Cloudflare parent zone by dns_delegation.tf)."
  value       = aws_route53_zone.triage.name_servers
}

output "delegation_records" {
  description = "NS records created in the Cloudflare parent zone, one per Route 53 name server."
  value = {
    for ns, r in cloudflare_dns_record.delegation : ns => {
      name    = r.name
      type    = r.type
      content = r.content
    }
  }
}

output "zone_id" {
  description = "Route 53 hosted zone id for later records and ACM validation."
  value       = aws_route53_zone.triage.zone_id
}

output "api_url" {
  description = "Base URL of the alert-ingest and console HTTP API."
  value       = "https://${local.api_domain}"
}

output "console_url" {
  description = "URL of the incident console."
  value       = local.console_origin
}

output "alarms_topic_arn" {
  description = "SNS topic that alarm producers (M4) publish to."
  value       = aws_sns_topic.alarms.arn
}

output "alerts_queue_url" {
  description = "SQS queue URL for the alerts pipeline."
  value       = aws_sqs_queue.alerts.id
}

output "alerts_dlq_url" {
  description = "SQS queue URL for the alerts dead-letter queue (bankops replay-dlq)."
  value       = aws_sqs_queue.alerts_dlq.id
}

output "hmac_secret_parameter" {
  description = "SSM parameter name holding the ingest webhook HMAC secret (read with --with-decryption)."
  value       = aws_ssm_parameter.ingest_hmac_secret.name
}

output "console_token_parameter" {
  description = "SSM parameter name holding the console/bankops bearer token (read with --with-decryption)."
  value       = aws_ssm_parameter.console_token.name
}
