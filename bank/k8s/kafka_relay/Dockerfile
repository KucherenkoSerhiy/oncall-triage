# kafka-relay: Prometheus-instrumented Kafka consumer that HMAC-signs and
# relays alerts.raw messages to the AWS ingest endpoint (M7b, route A).
# Build from the repo root:
#   docker build -f bank/k8s/kafka_relay/Dockerfile -t nordwind/kafka-relay:local .
FROM python:3.12-slim

RUN useradd --system --no-create-home --uid 10001 nordwind

WORKDIR /app

COPY bank/k8s/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY bank/k8s/_shared/ _shared/
COPY bank/k8s/kafka_relay/ kafka_relay/

USER nordwind

EXPOSE 8080

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=2)"]

CMD ["python", "-m", "kafka_relay"]
