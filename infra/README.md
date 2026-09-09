# Infrastructure

Everything that has a cloud API is Terraform. Four root modules, two
audiences:

| Root | Applied by | State | Contains |
|---|---|---|---|
| `bootstrap/aws` | a human, once | local file, then never touched | Terraform state bucket, GitHub OIDC provider, the deploy role `deploy.yml` assumes |
| `bootstrap/azure` | a human, once | local file | resource group, app registration + federated credentials for GitHub, role assignment scoped to the resource group |
| `aws` | `deploy.yml` (plan on PR, apply on merge) | `s3://<bucket>/aws/terraform.tfstate` (bucket in eu-north-1) | the triage brain, the AWS bank estate, DNS zone, budget, dashboard |
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

## What `infra/aws` deploys

The alert spine (M2): everything the triage brain needs to ingest an alert,
queue it, hand it to a worker, and let an operator read the result.

- **DynamoDB** (`storage.tf`): `alerts`, `verdicts`, `known-issues` -
  provisioned 5/5 capacity (2/2 on GSIs) to stay in the always-free tier.
- **SQS + SNS** (`messaging.tf`): the `alerts` queue (with a DLQ after 3
  failed attempts) and the `alarms` SNS topic that will carry M4's alarm
  producers into ingest.
- **Lambda** (`lambdas.tf`): `ingest`, `console-api`, `triage-worker` -
  Python 3.12 on arm64, one shared code zip, roles scoped to exactly the
  tables/queue/parameters each function touches.
- **API Gateway** (`api.tf`): an HTTP API at `api.<domain>` routing to
  `ingest` (`POST /alerts`) and `console-api` (everything else), with
  access logging and throttling.
- **Console** (`console.tf`): a private S3 bucket behind CloudFront (Origin
  Access Control) serving `console/` at the zone apex.
- **Secrets** (`secrets.tf`): two SSM `SecureString` parameters, generated
  in Terraform so no plaintext ever lands in the repo.

An operator using `bankops` against a deployed environment reads the two
generated secrets from SSM:

```bash
aws ssm get-parameter --with-decryption --name /nordwind-triage/demo/ingest-hmac-secret --query Parameter.Value --output text
aws ssm get-parameter --with-decryption --name /nordwind-triage/demo/console-token --query Parameter.Value --output text
```

## One-time account prerequisites (outside Terraform)

Some AWS services create a *service-linked role* the first time they are
used in an account. Creating one needs `iam:CreateServiceLinkedRole`, which
the deploy role deliberately does not hold, so these are created once by a
human session (CloudShell in the console is enough - no key involved):

```bash
# API Gateway custom domain names (used by infra/aws api.tf)
aws iam create-service-linked-role --aws-service-name ops.apigateway.amazonaws.com
```

Symptom when missing: `apply - aws` fails on `aws_apigatewayv2_domain_name`
with "Caller does not have permissions to create a Service Linked Role".
Re-running the deploy after the command succeeds continues from the saved
state.

## Conventions

- Provider default tags on every resource: `project`, `env`, `owner`,
  `cost_center`, `managed_by`; components additionally carry
  `c4_container` matching an identifier in `docs/c4/workspace.dsl` (the
  drift check keys on it).
- Names: `nordwind-triage-<env>-<component>`.
- `terraform fmt`, `validate`, `tflint` and `checkov` run in CI for all four
  roots; policy exceptions live in `.checkov.yaml` with a reason each.
