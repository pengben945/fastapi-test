# LogPulse HR

LogPulse HR 是一个企业员工管理系统，覆盖部门管理、员工档案、考勤打卡与薪资
结算等核心业务能力，适合用于演示企业级业务流程与基础管理场景。

## Quick start

1. Build and start the stack:

   ```bash
   docker compose up --build
   ```

2. Open:
   - App: `http://localhost:8000`
   - Prometheus: `http://localhost:9090`
   - Elasticsearch: `http://localhost:9200`

## Local run (without Docker)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317 uvicorn app.main:app --reload
```

## API Overview

- `POST /departments` create department
- `GET /departments` list departments
- `POST /employees` create employee
- `GET /employees/{id}` get employee
- `POST /employees/{id}/attendance` check-in/out
- `POST /payroll/run` simulate payroll run

## Configuration

- `SIM_ENABLED`: enable background simulation (default: true)
- `SIM_BASE_URL`: base URL for simulated traffic (default: http://127.0.0.1:8000)
- `SIM_MIN_WAIT`: min seconds between actions (default: 0.5)
- `SIM_MAX_WAIT`: max seconds between actions (default: 2.0)
- `LOG_LEVEL`: logging level (default: INFO)
