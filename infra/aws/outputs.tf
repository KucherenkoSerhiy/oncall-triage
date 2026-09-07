output "name_servers" {
  description = "Create NS records with these four values for `triage` at the parent domain's DNS."
  value       = aws_route53_zone.triage.name_servers
}

output "zone_id" {
  description = "Route 53 hosted zone id for later records and ACM validation."
  value       = aws_route53_zone.triage.zone_id
}
