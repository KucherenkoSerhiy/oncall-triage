# cards-authorization: Prometheus-instrumented HTTP service for the
# nordwind-bank Kubernetes estate (M6a). Build from the repo root:
#   docker build -f bank/k8s/cards_authorization/Dockerfile -t nordwind/cards-authorization:local .
FROM python:3.12-slim

RUN useradd --system --no-create-home --uid 10001 nordwind

WORKDIR /app

COPY bank/k8s/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY bank/k8s/_shared/ _shared/
COPY bank/k8s/cards_authorization/ cards_authorization/

USER nordwind

EXPOSE 8080

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=2)"]

CMD ["python", "-m", "cards_authorization"]
