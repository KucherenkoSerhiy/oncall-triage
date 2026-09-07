output "deploy_role_arn" {
  description = "Set as the GitHub repository variable AWS_DEPLOY_ROLE_ARN."
  value       = aws_iam_role.deploy.arn
}

output "state_bucket" {
  description = "Set as the GitHub repository variable TF_STATE_BUCKET."
  value       = aws_s3_bucket.tfstate.bucket
}

output "workload_boundary_arn" {
  description = "Permissions boundary every workload role created by infra/aws must carry."
  value       = aws_iam_policy.workload_boundary.arn
}
