# HTTP API: one route to ingest, the rest to the console API. CORS is
# handled inside the Lambda (services.console_api.http), not by API
# Gateway.

resource "aws_apigatewayv2_api" "triage" {
  name          = "${local.name_prefix}-api"
  protocol_type = "HTTP"

  tags = local.tags.api
}

resource "aws_lambda_permission" "api_invokes_ingest" {
  statement_id  = "AllowApiGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ingest.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.triage.execution_arn}/*/*"
}

resource "aws_lambda_permission" "api_invokes_console_api" {
  statement_id  = "AllowApiGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.console_api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.triage.execution_arn}/*/*"
}

resource "aws_apigatewayv2_integration" "ingest" {
  api_id                 = aws_apigatewayv2_api.triage.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.ingest.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_integration" "console_api" {
  api_id                 = aws_apigatewayv2_api.triage.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.console_api.invoke_arn
  payload_format_version = "2.0"
}

locals {
  console_api_routes = [
    "GET /health",
    "GET /alerts",
    "GET /alerts/{alert_id}",
    "GET /known-issues",
    "POST /known-issues",
    "DELETE /known-issues/{service}/{issue_id}",
    "OPTIONS /{proxy+}",
  ]
}

resource "aws_apigatewayv2_route" "ingest_alerts" {
  api_id    = aws_apigatewayv2_api.triage.id
  route_key = "POST /alerts"
  target    = "integrations/${aws_apigatewayv2_integration.ingest.id}"
}

resource "aws_apigatewayv2_route" "console_api" {
  for_each = toset(local.console_api_routes)

  api_id    = aws_apigatewayv2_api.triage.id
  route_key = each.value
  target    = "integrations/${aws_apigatewayv2_integration.console_api.id}"
}

resource "aws_cloudwatch_log_group" "api_access" {
  name              = "/aws/apigateway/${local.name_prefix}-api"
  retention_in_days = 14

  tags = local.tags.api
}

# HTTP API access logging writes through a resource policy, not the
# account-level CloudWatch role that REST APIs (v1) need.
data "aws_iam_policy_document" "api_access_logs" {
  statement {
    sid       = "ApiGatewayWriteAccessLogs"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.api_access.arn}:*"]

    principals {
      type        = "Service"
      identifiers = ["apigateway.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }

    condition {
      test     = "ArnLike"
      variable = "aws:SourceArn"
      values   = ["arn:aws:execute-api:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:${aws_apigatewayv2_api.triage.id}/*"]
    }
  }
}

resource "aws_cloudwatch_log_resource_policy" "api_access_logs" {
  policy_name     = "${local.name_prefix}-api-access-logs"
  policy_document = data.aws_iam_policy_document.api_access_logs.json
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.triage.id
  name        = "$default"
  auto_deploy = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_access.arn
    format = jsonencode({
      requestId               = "$context.requestId"
      routeKey                = "$context.routeKey"
      status                  = "$context.status"
      integrationErrorMessage = "$context.integrationErrorMessage"
      responseLatency         = "$context.responseLatency"
    })
  }

  default_route_settings {
    throttling_burst_limit = 20
    throttling_rate_limit  = 10
  }

  tags = local.tags.api
}

# ---------------------------------------------------------------- custom domain

resource "aws_acm_certificate" "api" {
  domain_name       = local.api_domain
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }

  tags = local.tags.api
}

resource "aws_route53_record" "api_cert_validation" {
  for_each = {
    for dvo in aws_acm_certificate.api.domain_validation_options : dvo.domain_name => {
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

resource "aws_acm_certificate_validation" "api" {
  certificate_arn         = aws_acm_certificate.api.arn
  validation_record_fqdns = [for r in aws_route53_record.api_cert_validation : r.fqdn]
}

resource "aws_apigatewayv2_domain_name" "api" {
  domain_name = local.api_domain

  domain_name_configuration {
    certificate_arn = aws_acm_certificate_validation.api.certificate_arn
    endpoint_type   = "REGIONAL"
    security_policy = "TLS_1_2"
  }

  tags = local.tags.api
}

resource "aws_apigatewayv2_api_mapping" "api" {
  api_id      = aws_apigatewayv2_api.triage.id
  domain_name = aws_apigatewayv2_domain_name.api.id
  stage       = aws_apigatewayv2_stage.default.id
}

resource "aws_route53_record" "api" {
  zone_id = aws_route53_zone.triage.zone_id
  name    = local.api_domain
  type    = "A"

  alias {
    name                   = aws_apigatewayv2_domain_name.api.domain_name_configuration[0].target_domain_name
    zone_id                = aws_apigatewayv2_domain_name.api.domain_name_configuration[0].hosted_zone_id
    evaluate_target_health = false
  }
}
