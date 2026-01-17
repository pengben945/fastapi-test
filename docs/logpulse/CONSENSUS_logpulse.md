# Consensus - LogPulse

## Requirement summary
- Build a FastAPI employee management service named LogPulse HR.
- Simulate usage to continuously generate logs and metrics.
- Export telemetry via OpenTelemetry OTLP to a collector.
- Collector sends logs to Elasticsearch and metrics to Prometheus.

## Acceptance criteria
- App boots and exposes `/`, `/departments`, `/employees`, `/attendance`,
  `/payroll`.
- Background simulator generates requests without external users.
- Logs appear in Elasticsearch index `logpulse-logs`.
- Metrics are scraped by Prometheus from collector endpoint `:9464`.
- `docker compose up --build` runs the full stack.

## Technical plan
- FastAPI app with custom middleware for metrics and structured logs.
- OpenTelemetry SDK configured for traces, metrics, logs with OTLP exporters.
- OpenTelemetry Collector config with `otlp` receiver, `elasticsearch` and
  `prometheus` exporters.
- Prometheus configuration to scrape collector.

## Constraints
- Keep the system lightweight and demo-oriented.
- Do not store any secrets in the repository.

