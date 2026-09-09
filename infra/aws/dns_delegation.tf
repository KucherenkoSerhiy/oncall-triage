# ------------------------------------------------- NS delegation (Cloudflare)
# The parent zone (var.parent_domain) is hosted on Cloudflare. One NS
# record per Route 53 name server delegates `triage` to the hosted zone
# above, so the delegation follows the zone: recreate the zone and the
# records update themselves. The provider reads CLOUDFLARE_API_TOKEN from
# the environment (deploy.yml); the token is scoped to Zone:Read +
# DNS:Edit on the parent zone only. Cloudflare record `tags` need a paid
# plan, hence `comment` carries the ownership marker instead.

provider "cloudflare" {}

data "cloudflare_zones" "parent" {
  name = var.parent_domain
}

locals {
  parent_zone_id = data.cloudflare_zones.parent.result[0].id
}

resource "cloudflare_dns_record" "delegation" {
  for_each = toset(aws_route53_zone.triage.name_servers)

  zone_id = local.parent_zone_id
  # Fully qualified on purpose: the Cloudflare API returns FQDNs, so a
  # relative "triage" would show a permanent diff on provider 5.x.
  name    = var.domain
  type    = "NS"
  content = each.value
  ttl     = 3600
  proxied = false
  comment = "Delegation of triage.* to Route 53 (managed by Terraform, oncall-triage repo)"
}
