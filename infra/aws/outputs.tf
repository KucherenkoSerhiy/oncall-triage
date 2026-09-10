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

output "hmac_secret_parameter" {
  description = "SSM parameter name holding the ingest webhook HMAC secret (read with --with-decryption)."
  value       = aws_ssm_parameter.ingest_hmac_secret.name
}

output "console_token_parameter" {
  description = "SSM parameter name holding the console/bankops bearer token (read with --with-decryption)."
  value       = aws_ssm_parameter.console_token.name
}

output "dnssec_ds_record" {
  description = "DS record to publish at the parent (key tag, algorithm, digest type, digest) - also what dns_check.py compares the Cloudflare DS against."
  value       = var.enable_dnssec ? "${aws_route53_key_signing_key.triage[0].key_tag} ${aws_route53_key_signing_key.triage[0].signing_algorithm_type} ${aws_route53_key_signing_key.triage[0].digest_algorithm_type} ${aws_route53_key_signing_key.triage[0].digest_value}" : "DNSSEC not enabled (enable_dnssec=false)"
}

output "dns_query_log_group" {
  description = "CloudWatch Logs group receiving Route 53 query logs for the delegated zone."
  value       = aws_cloudwatch_log_group.dns_queries.name
}
