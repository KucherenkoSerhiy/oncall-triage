# DynamoDB: the alert log, one verdict per alert, and taught known issues.
# PROVISIONED (not on-demand) to stay inside the AWS always-free tier - see
# docs/specs/m2c-spine-terraform-console.md requirement 2.

resource "aws_dynamodb_table" "alerts" {
  name           = "${local.name_prefix}-alerts"
  billing_mode   = "PROVISIONED"
  read_capacity  = 5
  write_capacity = 5
  hash_key       = "alert_id"

  attribute {
    name = "alert_id"
    type = "S"
  }

  attribute {
    name = "fingerprint"
    type = "S"
  }

  attribute {
    name = "status"
    type = "S"
  }

  attribute {
    name = "received_at"
    type = "S"
  }

  global_secondary_index {
    name            = "by_fingerprint"
    hash_key        = "fingerprint"
    range_key       = "received_at"
    projection_type = "ALL"
    read_capacity   = 2
    write_capacity  = 2
  }

  global_secondary_index {
    name            = "by_status"
    hash_key        = "status"
    range_key       = "received_at"
    projection_type = "ALL"
    read_capacity   = 2
    write_capacity  = 2
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = local.tags.store
}

resource "aws_dynamodb_table" "verdicts" {
  name           = "${local.name_prefix}-verdicts"
  billing_mode   = "PROVISIONED"
  read_capacity  = 5
  write_capacity = 5
  hash_key       = "alert_id"

  attribute {
    name = "alert_id"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = local.tags.store
}

resource "aws_dynamodb_table" "known_issues" {
  name           = "${local.name_prefix}-known-issues"
  billing_mode   = "PROVISIONED"
  read_capacity  = 5
  write_capacity = 5
  hash_key       = "service"
  range_key      = "issue_id"

  attribute {
    name = "service"
    type = "S"
  }

  attribute {
    name = "issue_id"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = local.tags.store
}
