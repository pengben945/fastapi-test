# Design - LogPulse

## Architecture

```mermaid
flowchart LR
  UserSim[Simulator]
  App[FastAPI App]
  OTelSDK[OpenTelemetry SDK]
  Collector[OTel Collector]
  ES[Elasticsearch]
  Prom[Prometheus]

  UserSim -->|HTTP| App
  App -->|Logs/Metrics/Traces (OTLP)| OTelSDK
  OTelSDK -->|OTLP| Collector
  Collector -->|Logs/Traces| ES
  Collector -->|Metrics| Prom
```

## Components
- FastAPI app: endpoints, middleware, and business logic.
- Simulator: background task generating HTTP requests.
- OTel SDK: traces, metrics, logs instrumentation.
- Collector: OTLP receiver, Elasticsearch exporter, Prometheus exporter.

## Interfaces
- HTTP endpoints:
  - `GET /` health
  - `POST /departments` body: `{ name }`
  - `GET /departments`
  - `POST /employees` body: `{ name, department_id, title }`
  - `GET /employees/{id}`
  - `POST /employees/{id}/attendance` body: `{ status }`
  - `POST /payroll/run` body: `{ month }`
- OTLP endpoint: `4317` (gRPC), `4318` (HTTP)
- Prometheus scrape endpoint: `9464`

## Data flow
1. Simulator calls FastAPI endpoints.
2. App logs and metrics emitted via OTel SDK.
3. Collector receives OTLP data.
4. Collector exports logs to Elasticsearch and metrics to Prometheus.

## Error handling
- Invalid input yields 4xx errors and logs warnings.
- Payment risk yields 402 and logs errors.

