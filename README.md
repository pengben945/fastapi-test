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

## Public access without domain (self-signed TLS)

This setup exposes Elasticsearch and Prometheus through Nginx on port 443 with
Basic Auth and a self-signed certificate.

### Steps on EC2

1. Generate a self-signed certificate (replace with your public IP):

   ```bash
   chmod +x scripts/gen-self-signed-cert.sh
   ./scripts/gen-self-signed-cert.sh 47.128.81.143
   ```

2. Create Basic Auth credentials:

   ```bash
   sudo apt install -y apache2-utils
   htpasswd -c nginx/.htpasswd admin
   ```

3. Start the stack:

   ```bash
   docker compose up -d
   ```

### Access

- Elasticsearch: `https://<PUBLIC_IP>/es/`
- Prometheus: `https://<PUBLIC_IP>/prom/`

Browsers will warn about the self-signed certificate. Use "Proceed anyway" or
configure your client to skip TLS verification.

## Configuration

- `SIM_ENABLED`: enable background simulation (default: true)
- `SIM_BASE_URL`: base URL for simulated traffic (default: http://127.0.0.1:8000)
- `SIM_MIN_WAIT`: min seconds between actions (default: 0.5)
- `SIM_MAX_WAIT`: max seconds between actions (default: 2.0)
- `LOG_LEVEL`: logging level (default: INFO)
