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
