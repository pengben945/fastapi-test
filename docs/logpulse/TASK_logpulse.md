# Task Plan - LogPulse

## Task 1: FastAPI scaffolding
- Inputs: empty repo
- Outputs: `app/main.py`, `app/otel.py`, `app/sim.py`, `requirements.txt`
- Acceptance: app starts and endpoints respond

## Task 2: Telemetry pipeline
- Inputs: OTLP exporter config
- Outputs: `otel-collector-config.yaml`, `prometheus.yml`
- Acceptance: collector exposes metrics on `:9464`

## Task 3: Container stack
- Inputs: docker-compose design
- Outputs: `Dockerfile`, `docker-compose.yml`
- Acceptance: stack starts with ES, Prometheus, collector, app

## Task 4: Tests and docs
- Inputs: app API
- Outputs: pytest tests, README, 6A docs
- Acceptance: tests pass, docs explain setup

## Dependencies
- Task 2 depends on Task 1
- Task 3 depends on Task 2
- Task 4 depends on Tasks 1-3

