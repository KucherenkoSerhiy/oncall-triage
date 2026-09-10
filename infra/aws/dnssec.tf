# DNSSEC for the delegated zone, plus the DS record that publishes the
# chain of trust at the parent (Cloudflare), plus Route 53 query logging.
# The signing key must live in us-east-1 (a Route 53 requirement); the
# provider alias is declared in console.tf (also used for the CloudFront
# certificate).

resource "aws_kms_key" "dnssec" {
  provider = aws.us_east_1

  description              = "DNSSEC signing key for ${aws_route53_zone.triage.name}"
  customer_master_key_spec = "ECC_NIST_P256"
  key_usage                = "SIGN_VERIFY"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "RouteFiftyThreeDnssecSign"
        Effect = "Allow"
        Principal = {
          Service = "dnssec-route53.amazonaws.com"
        }
        Action   = ["kms:DescribeKey", "kms:GetPublicKey", "kms:Sign"]
        Resource = "*"
        Condition = {
          StringEquals = { "aws:SourceAccount" = data.aws_caller_identity.current.account_id }
          ArnLike      = { "aws:SourceArn" = "arn:aws:route53:::hostedzone/${aws_route53_zone.triage.zone_id}" }
        }
      },
      {
        Sid    = "RouteFiftyThreeDnssecCreateGrant"
        Effect = "Allow"
        Principal = {
          Service = "dnssec-route53.amazonaws.com"
        }
        Action   = "kms:CreateGrant"
        Resource = "*"
        Condition = {
          Bool = { "kms:GrantIsForAWSResource" = "true" }
        }
      },
      {
        Sid       = "AccountRootAdmin"
        Effect    = "Allow"
        Principal = { AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root" }
        Action    = "kms:*"
        Resource  = "*"
      }
    ]
  })

  tags = local.tags.dns
}

resource "aws_kms_alias" "dnssec" {
  provider = aws.us_east_1

  name          = "alias/${local.name_prefix}-dnssec"
  target_key_id = aws_kms_key.dnssec.key_id
}

resource "aws_route53_key_signing_key" "triage" {
  hosted_zone_id             = aws_route53_zone.triage.id
  key_management_service_arn = aws_kms_key.dnssec.arn
  name                       = "${local.name_prefix}-ksk"
  status                     = "ACTIVE"
}

resource "aws_route53_hosted_zone_dnssec" "triage" {
  hosted_zone_id = aws_route53_zone.triage.id

  depends_on = [aws_route53_key_signing_key.triage]
}

# The chain of trust at the parent. Ordering matters both ways:
# - create: `depends_on` the hosted-zone DNSSEC resource, so the DS record
#   is only published once zone signing is enabled (and, per AWS guidance,
#   time is left for it to propagate before a resolver goes looking for it
#   - see infra/README.md "DNSSEC" for the wait).
# - destroy: Terraform tears down in the reverse of that same order, i.e.
#   the DS record is removed *before* signing is disabled - the correct
#   order (a stale DS pointing at a since-disabled KSK is what breaks
#   resolution for the whole zone), and it falls out of this one
#   `depends_on` with no extra ordering resource needed.
resource "cloudflare_dns_record" "ds" {
  zone_id = local.parent_zone_id
  # Fully qualified, matching the NS delegation records in dns_delegation.tf.
  name = var.domain
  type = "DS"
  ttl  = 3600
  data = {
    key_tag     = aws_route53_key_signing_key.triage.key_tag
    algorithm   = aws_route53_key_signing_key.triage.signing_algorithm_type
    digest_type = aws_route53_key_signing_key.triage.digest_algorithm_type
    digest      = aws_route53_key_signing_key.triage.digest_value
  }
  comment = "DS for triage.* DNSSEC chain of trust (managed by Terraform, oncall-triage repo)"

  depends_on = [aws_route53_hosted_zone_dnssec.triage]
}

# Query logging: who is asking the zone what. Log group must also be in
# us-east-1 (same Route 53 requirement as the signing key).
resource "aws_cloudwatch_log_group" "dns_queries" {
  provider = aws.us_east_1

  name              = "/aws/route53/${local.name_prefix}"
  retention_in_days = 7

  tags = local.tags.dns
}

data "aws_iam_policy_document" "dns_queries" {
  statement {
    sid    = "Route53LogsDelivery"
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["route53.amazonaws.com"]
    }
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.dns_queries.arn}:*"]
  }
}

resource "aws_cloudwatch_log_resource_policy" "dns_queries" {
  provider = aws.us_east_1

  policy_name     = "${local.name_prefix}-dns-queries"
  policy_document = data.aws_iam_policy_document.dns_queries.json
  # Scopes the policy to this one log group instead of the account-wide
  # default, so it doesn't count against the 10-resource-policy account
  # limit shared with every other CloudWatch Logs subscriber.
  resource_arn = aws_cloudwatch_log_group.dns_queries.arn
}

resource "aws_route53_query_log" "triage" {
  zone_id                  = aws_route53_zone.triage.zone_id
  cloudwatch_log_group_arn = aws_cloudwatch_log_group.dns_queries.arn

  depends_on = [aws_cloudwatch_log_resource_policy.dns_queries]
}
