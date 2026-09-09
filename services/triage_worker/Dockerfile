# Image-based Lambda for the triage worker. Built and pushed by the `image`
# job in .github/workflows/deploy.yml (tagged `sha-<git sha>` and `latest`,
# pushed to the ECR repository infra/aws-ecr creates); `task worker:build`
# builds it locally for `task worker:local`.
FROM --platform=linux/arm64 public.ecr.aws/lambda/python:3.12

COPY requirements.txt ${LAMBDA_TASK_ROOT}/requirements.txt
RUN pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements.txt

COPY oncall_triage/ ${LAMBDA_TASK_ROOT}/oncall_triage/
COPY services/ingest/ ${LAMBDA_TASK_ROOT}/services/ingest/
COPY services/triage_worker/ ${LAMBDA_TASK_ROOT}/services/triage_worker/

CMD ["services.triage_worker.handler.lambda_handler"]
