output "worker_repository_url" {
  description = "ECR repository URL for the triage-worker image; infra/aws reads it back with data \"aws_ecr_repository\", and deploy.yml's `image` job pushes to it directly."
  value       = aws_ecr_repository.triage_worker.repository_url
}

output "worker_repository_name" {
  description = "Bare repository name, for CLI calls (e.g. deleting a mutable tag before re-push) that need a name rather than a URL."
  value       = aws_ecr_repository.triage_worker.name
}
