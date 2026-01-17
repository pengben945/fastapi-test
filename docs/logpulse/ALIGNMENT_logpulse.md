# Alignment - LogPulse

## Project context
- Repository is empty; no existing modules or dependencies.
- Target stack: FastAPI + OpenTelemetry + Elasticsearch + Prometheus.

## Original request
Build a FastAPI employee management system that simulates usage to generate
logs and metrics, collected via OpenTelemetry into Elasticsearch and
Prometheus. Business logic can be designed as needed.

## Scope boundaries
- In scope: FastAPI app, OpenTelemetry SDK wiring, simulation task, Docker
  compose stack with collector, ES, Prometheus, and minimal tests.
- Out of scope: real authentication, persistence, dashboards, and production
  hardening.

## Understanding of requirements
- The system must emit logs and metrics even without real users.
- Telemetry must be exported via OTLP to an OpenTelemetry Collector, which
  forwards logs to Elasticsearch and metrics to Prometheus.
- Provide a usable run path for local and docker environments.

## Assumptions & decisions
- Use a background simulator that calls local endpoints via HTTP.
- Provide employee management endpoints for departments, employees, attendance,
  and payroll.
- Use OTLP gRPC exporter for all signals.
- Collector exports logs and traces to Elasticsearch, metrics to Prometheus.

## Open questions resolved by assumptions
- Specific business domain: simulate HR operations.
- Deployment style: docker-compose for a complete demo stack.

