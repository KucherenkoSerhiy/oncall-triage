#!/usr/bin/env bash
# Record the console view and publish it as demo/snapshot.json (#131).
#
# Run by the smoke job (deploy.yml) and by estate-demo after their probes,
# with AWS credentials from the deploy role, infra/aws initialised (outputs
# only) and SMOKE_TOKEN in the environment. The object sits next to the
# console files in the same private bucket and is served by CloudFront; the
# console loads it when no token is stored.
set -euo pipefail

python scripts/snapshot.py snapshot.json

bucket=$(terraform -chdir=infra/aws output -raw console_bucket)
distribution=$(terraform -chdir=infra/aws output -raw console_distribution_id)

aws s3 cp snapshot.json "s3://${bucket}/demo/snapshot.json" \
  --content-type application/json \
  --cache-control "public, max-age=300"

aws cloudfront create-invalidation \
  --distribution-id "${distribution}" \
  --paths "/demo/*" \
  --query Invalidation.Id --output text
