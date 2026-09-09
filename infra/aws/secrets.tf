# Generated once, here, so no plaintext ever lands in the repo. lambdas.tf
# reads these back via `data.aws_ssm_parameter` to populate Lambda
# environment variables - see the comment there for that trade-off.

resource "random_password" "ingest_hmac_secret" {
  length  = 48
  special = true
}

resource "random_password" "console_token" {
  length  = 32
  special = false
}

resource "aws_ssm_parameter" "ingest_hmac_secret" {
  name  = "/${var.project}/${var.environment}/ingest-hmac-secret"
  type  = "SecureString"
  value = random_password.ingest_hmac_secret.result

  tags = local.tags.secrets
}

resource "aws_ssm_parameter" "console_token" {
  name  = "/${var.project}/${var.environment}/console-token"
  type  = "SecureString"
  value = random_password.console_token.result

  tags = local.tags.secrets
}
