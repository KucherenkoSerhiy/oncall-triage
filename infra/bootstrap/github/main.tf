# Applied once by a human (GITHUB_TOKEN in the operator's shell - a
# personal access token with the repo scope on this repository is enough).
# Manages the two GitHub Actions environments deploy.yml's jobs run in:
# `plan` (PR plans, no protection) and `demo` (applies, one required
# reviewer, no wait timer). `demo` already exists (created by hand before
# this root existed) and is imported rather than recreated - see
# infra/README.md for the exact `terraform import` command.

provider "github" {
  owner = var.github_owner
}

# Numeric id required by the reviewers block below. If the provider cannot
# set a reviewer on this repository (see infra/README.md's fallback note
# for personal, non-organization repositories), drop the `reviewers` block
# from github_repository_environment.demo and set the reviewer by hand in
# the repository's Settings -> Environments -> demo instead.
data "github_user" "owner" {
  username = var.github_owner
}

resource "github_repository_environment" "plan" {
  repository  = var.github_repo
  environment = "plan"
}

resource "github_repository_environment" "demo" {
  repository  = var.github_repo
  environment = "demo"
  wait_timer  = 0

  reviewers {
    users = [data.github_user.owner.id]
  }
}
