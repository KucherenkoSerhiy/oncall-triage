# Implementation decisions - M2c (alert spine in Terraform, static console, smoke probe)

Notes on places where the spec text needed a judgment call to produce a
working system, or where a reasonable default had to be picked.

## `data.archive_file` source directory

The spec's requirement 4 gives `source_dir = "${path.module}/../../services"`
but also says the excludes list should exclude `cli/` and that the handler
paths are dotted as `services.ingest.handler.lambda_handler`. Those two
things are inconsistent with a literal reading:

- `cli/` is a sibling of `services/` at the repo root, not something inside
  `services/` - excluding it only makes sense if the zip is built from the
  repo root.
- The dotted handler paths require a top-level `services` package *inside*
  the zip. If `source_dir` pointed at `services/` itself, the zip root
  would be the *contents* of `services/` (`ingest/`, `console_api/`, ...)
  with no `services` package at all, and every handler would fail to
  import.

`infra/aws/lambdas.tf` therefore builds the zip from the repo root
(`"${path.module}/../.."`) and excludes everything except `services/**`
(explicitly listing `cli/`, `tests/`, `docs/`, caches, READMEs, etc.),
which satisfies both the working handler paths and the explicit `cli/`
exclusion. Verified by building the archive standalone and inspecting its
contents (`services/__init__.py`, `services/ingest/handler.py`, etc. present;
no `cli/`, `tests/`, or cache directories).

## Console-API IAM policy: split narrower than the summary text

Requirement 4 describes the console-api role's DynamoDB access as
"Query/GetItem/PutItem/DeleteItem on the three tables" - read as a set of
actions used across the three tables, not a grant of all four actions on
every table. `services/console_api/store.py` only ever queries/gets the
`alerts` and `verdicts` tables and only ever writes (Put/Delete) to
`known_issues`. The inline policy in `lambdas.tf` reflects that: a
`Query`/`GetItem` statement for `alerts` + `verdicts`, and a separate
`Query`/`GetItem`/`PutItem`/`DeleteItem` statement for `known_issues`. This
is strictly narrower than a literal "all four actions on all three tables"
reading and covers every DynamoDB call the handler actually makes.

## C4 deployment view: `triage.api` moved, not duplicated, into "API Gateway"

Requirement 10 asks to add an `API Gateway` deployment node for
`triage.api` "if it is not there". `triage.api` was previously modelled as
a `containerInstance` inside the existing "Lambda" deployment node.
Structurizr's deployment model allows the same container to be
instantiated in more than one deployment node (that's how replicas across
AZs are usually modelled), but here it would just be modelling the same
single Lambda function twice for no reason. Instead, `triage.api` was
moved out of "Lambda" and into the new "API Gateway" node, since the API
Gateway is the container's actual front door in the deployment view.

## Checkov skips

Every new skip added to `.checkov.yaml` for this milestone carries its own
reason inline (see the "M2c" block). Most are either an explicit spec
requirement (SSE default on DynamoDB/SSM, 14-day log retention, WAF/VPC/
X-Ray as non-requirements) or a real v1 cost/scope trade-off already
called out in `lambdas.tf`'s comment about plaintext secrets in Lambda
environment variables. Where a fix was free (SNS topic KMS key, a
CloudFront response-headers policy, an S3 lifecycle rule on the console
bucket), the resource was fixed instead of skipped.
