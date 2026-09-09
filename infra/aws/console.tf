# The incident console: a private S3 bucket behind CloudFront (Origin
# Access Control), serving the static site in `console/` at the zone apex.
# ACM certificates for CloudFront must live in us-east-1 regardless of the
# stack's region.

provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"

  default_tags {
    tags = {
      project     = var.project
      env         = var.environment
      owner       = "serhiy"
      cost_center = "portfolio"
      managed_by  = "terraform/aws"
    }
  }
}

resource "aws_s3_bucket" "console" {
  bucket = "${local.name_prefix}-console"

  tags = local.tags.console
}

resource "aws_s3_bucket_versioning" "console" {
  bucket = aws_s3_bucket.console.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "console" {
  bucket = aws_s3_bucket.console.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "console" {
  bucket = aws_s3_bucket.console.id

  rule {
    id     = "expire-old-object-versions"
    status = "Enabled"

    filter {}

    noncurrent_version_expiration {
      noncurrent_days = 90
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

resource "aws_s3_bucket_public_access_block" "console" {
  bucket                  = aws_s3_bucket.console.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

data "aws_iam_policy_document" "console_bucket" {
  statement {
    sid       = "AllowCloudFrontOAC"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.console.arn}/*"]

    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [aws_cloudfront_distribution.console.arn]
    }
  }
}

resource "aws_s3_bucket_policy" "console" {
  bucket = aws_s3_bucket.console.id
  policy = data.aws_iam_policy_document.console_bucket.json
}

locals {
  console_dir   = "${path.module}/../../console"
  console_files = fileset(local.console_dir, "**")

  content_types = {
    html = "text/html"
    js   = "application/javascript"
    css  = "text/css"
    json = "application/json"
  }
}

resource "aws_s3_object" "console" {
  for_each = local.console_files

  bucket       = aws_s3_bucket.console.id
  key          = each.value
  source       = "${local.console_dir}/${each.value}"
  etag         = filemd5("${local.console_dir}/${each.value}")
  content_type = lookup(local.content_types, split(".", each.value)[length(split(".", each.value)) - 1], "application/octet-stream")
}

# ---------------------------------------------------------------- CloudFront

resource "aws_cloudfront_origin_access_control" "console" {
  name                              = "${local.name_prefix}-console"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

data "aws_cloudfront_cache_policy" "caching_optimized" {
  name = "Managed-CachingOptimized"
}

data "aws_cloudfront_response_headers_policy" "security_headers" {
  name = "Managed-SecurityHeadersPolicy"
}

resource "aws_acm_certificate" "console" {
  provider = aws.us_east_1

  domain_name       = var.domain
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }

  tags = local.tags.console
}

resource "aws_route53_record" "console_cert_validation" {
  for_each = {
    for dvo in aws_acm_certificate.console.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      type   = dvo.resource_record_type
      record = dvo.resource_record_value
    }
  }

  zone_id = aws_route53_zone.triage.zone_id
  name    = each.value.name
  type    = each.value.type
  records = [each.value.record]
  ttl     = 300
}

resource "aws_acm_certificate_validation" "console" {
  provider = aws.us_east_1

  certificate_arn         = aws_acm_certificate.console.arn
  validation_record_fqdns = [for r in aws_route53_record.console_cert_validation : r.fqdn]
}

resource "aws_cloudfront_distribution" "console" {
  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = "index.html"
  price_class         = "PriceClass_100"
  aliases             = [var.domain]
  comment             = "${local.name_prefix}-console"

  origin {
    domain_name              = aws_s3_bucket.console.bucket_regional_domain_name
    origin_id                = "console-s3"
    origin_access_control_id = aws_cloudfront_origin_access_control.console.id
  }

  default_cache_behavior {
    allowed_methods            = ["GET", "HEAD"]
    cached_methods             = ["GET", "HEAD"]
    target_origin_id           = "console-s3"
    viewer_protocol_policy     = "redirect-to-https"
    cache_policy_id            = data.aws_cloudfront_cache_policy.caching_optimized.id
    response_headers_policy_id = data.aws_cloudfront_response_headers_policy.security_headers.id
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    acm_certificate_arn      = aws_acm_certificate_validation.console.certificate_arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }

  tags = local.tags.console
}

resource "aws_route53_record" "console_a" {
  zone_id = aws_route53_zone.triage.zone_id
  name    = var.domain
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.console.domain_name
    zone_id                = aws_cloudfront_distribution.console.hosted_zone_id
    evaluate_target_health = false
  }
}

resource "aws_route53_record" "console_aaaa" {
  zone_id = aws_route53_zone.triage.zone_id
  name    = var.domain
  type    = "AAAA"

  alias {
    name                   = aws_cloudfront_distribution.console.domain_name
    zone_id                = aws_cloudfront_distribution.console.hosted_zone_id
    evaluate_target_health = false
  }
}
