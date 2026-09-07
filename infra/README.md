# Infrastructure

Everything that has a cloud API is Terraform. Four root modules, two
audiences:

| Root | Applied by | State | Contains |
|---|---|---|---|
| `bootstrap/aws` | a human, once | local file, then never touched | Terraform state bucket, GitHub OIDC provider, the deploy role `deploy.yml` assumes |
| `bootstrap/azure` | a human, once | local file | resource group, app registration + federated credentials for GitHub, role assignment scoped to the resource group |
| `aws` | `deploy.yml` (plan on PR, apply on merge) | `s3://<bucket>/aws/terraform.tfstate` | the triage brain, the AWS bank estate, DNS zone, budget, dashboard |
| `azure` | `deploy.yml` | `s3://<bucket>/azure/terraform.tfstate` | the Azure bank estate, alert forwarder, Azure Monitor rules, budget |

The bootstrap modules are the only place a human credential is ever used;
their outputs become GitHub repository *variables* (not secrets - none of
them is secret): `AWS_DEPLOY_ROLE_ARN`, `TF_STATE_BUCKET`, `AZURE_CLIENT_ID`,
`AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`. The one real secret,
`BUDGET_EMAIL`, is an environment secret only because it is personal data.

## Bootstrap (once)

```bash
# AWS - needs an identity that can create IAM roles and S3 buckets
cd infra/bootstrap/aws
terraform init && terraform apply
terraform output            # -> deploy_role_arn, state_bucket

# Azure - needs `az login` with rights to create app registrations
cd ../azure
terraform init && terraform apply
terraform output            # -> client_id, tenant_id, subscription_id
```

Then set the five repository variables in GitHub, create the `demo`
environment with yourself as required reviewer, and every later change
flows through pull requests.

## Conventions

- Provider default tags on every resource: `project`, `env`, `owner`,
  `cost_center`, `managed_by`; components additionally carry
  `c4_container` matching an identifier in `docs/c4/workspace.dsl` (the
  drift check keys on it).
- Names: `nordwind-triage-<env>-<component>`.
- `terraform fmt`, `validate`, `tflint` and `checkov` run in CI for all four
  roots; policy exceptions live in `.checkov.yaml` with a reason each.
