output "plan_environment" {
  description = "Environment name deploy.yml's plan jobs declare."
  value       = github_repository_environment.plan.environment
}

output "demo_environment" {
  description = "Environment name deploy.yml's apply jobs declare."
  value       = github_repository_environment.demo.environment
}
