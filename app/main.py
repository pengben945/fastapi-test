import asyncio
import logging
import os
import random
import time

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from opentelemetry import metrics
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from app.otel import setup_logging, setup_telemetry
from app.sim import create_simulator


SERVICE_NAME = "logpulse"
logger = logging.getLogger("logpulse.app")
meter = metrics.get_meter(SERVICE_NAME)
request_counter = meter.create_counter(
    "app_requests_total", description="Total number of requests"
)
request_latency = meter.create_histogram(
    "app_request_latency_ms", description="Request latency in milliseconds"
)
employee_created = meter.create_counter(
    "employee_created_total", description="Employees created"
)
attendance_checkins = meter.create_counter(
    "attendance_checkins_total", description="Attendance check-ins"
)
payroll_runs = meter.create_counter(
    "payroll_runs_total", description="Payroll runs"
)


class DepartmentCreate(BaseModel):
    name: str


class EmployeeCreate(BaseModel):
    name: str
    department_id: int
    title: str


class AttendancePayload(BaseModel):
    status: str


class PayrollRunPayload(BaseModel):
    month: str


def create_app() -> FastAPI:
    setup_logging()
    setup_telemetry(SERVICE_NAME)

    app = FastAPI(title="LogPulse HR", version="0.2.0")
    FastAPIInstrumentor.instrument_app(app)
    app.state.simulator = None
    app.state.departments = {}
    app.state.employees = {}
    app.state.attendance = []
    app.state.next_department_id = 1
    app.state.next_employee_id = 1000

    @app.middleware("http")
    async def metrics_middleware(request: Request, call_next):
        start = time.perf_counter()
        response = None
        try:
            response = await call_next(request)
            return response
        finally:
            duration_ms = (time.perf_counter() - start) * 1000
            request_latency.record(
                duration_ms, {"method": request.method, "path": request.url.path}
            )
            status_code = str(response.status_code) if response else "500"
            request_counter.add(
                1,
                {
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code,
                },
            )

    @app.get("/")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": SERVICE_NAME}

    @app.post("/departments")
    async def create_department(payload: DepartmentCreate) -> dict[str, int | str]:
        if not payload.name.strip():
            raise HTTPException(status_code=400, detail="invalid department name")
        department_id = app.state.next_department_id
        app.state.next_department_id += 1
        app.state.departments[department_id] = {"id": department_id, "name": payload.name}
        logger.info("department created id=%s name=%s", department_id, payload.name)
        return {"id": department_id, "name": payload.name}

    @app.get("/departments")
    async def list_departments() -> dict[str, list[dict[str, int | str]]]:
        return {"items": list(app.state.departments.values())}

    @app.post("/employees")
    async def create_employee(payload: EmployeeCreate) -> dict[str, int | str]:
        if payload.department_id not in app.state.departments:
            raise HTTPException(status_code=404, detail="department not found")
        employee_id = app.state.next_employee_id
        app.state.next_employee_id += 1
        employee = {
            "id": employee_id,
            "name": payload.name,
            "department_id": payload.department_id,
            "title": payload.title,
        }
        app.state.employees[employee_id] = employee
        employee_created.add(1, {"department_id": str(payload.department_id)})
        logger.info("employee created id=%s department=%s", employee_id, payload.department_id)
        return employee

    @app.get("/employees/{employee_id}")
    async def get_employee(employee_id: int) -> dict[str, int | str]:
        employee = app.state.employees.get(employee_id)
        if not employee:
            raise HTTPException(status_code=404, detail="employee not found")
        return employee

    @app.post("/employees/{employee_id}/attendance")
    async def checkin(employee_id: int, payload: AttendancePayload) -> dict[str, str]:
        employee = app.state.employees.get(employee_id)
        if not employee:
            raise HTTPException(status_code=404, detail="employee not found")
        status = payload.status.lower()
        if status not in {"in", "out"}:
            raise HTTPException(status_code=400, detail="invalid attendance status")
        record = {"employee_id": employee_id, "status": status, "ts": time.time()}
        app.state.attendance.append(record)
        attendance_checkins.add(1, {"status": status})
        logger.info("attendance %s employee_id=%s", status, employee_id)
        return {"status": "ok"}

    @app.post("/payroll/run")
    async def run_payroll(payload: PayrollRunPayload) -> dict[str, int | str]:
        if not payload.month or len(payload.month) != 7 or payload.month[4] != "-":
            raise HTTPException(status_code=400, detail="invalid month format")
        await asyncio.sleep(random.uniform(0.05, 0.2))
        payroll_runs.add(1, {"month": payload.month})
        logger.info("payroll run month=%s employees=%s", payload.month, len(app.state.employees))
        return {"status": "ok", "month": payload.month, "employees": len(app.state.employees)}

    @app.on_event("startup")
    async def start_simulation() -> None:
        sim_enabled = os.getenv("SIM_ENABLED", "true").lower() in {"1", "true", "yes"}
        if sim_enabled:
            simulator = create_simulator()
            simulator.start()
            app.state.simulator = simulator
            logger.info("simulator started")

    @app.on_event("shutdown")
    async def stop_simulation() -> None:
        simulator = app.state.simulator
        if simulator is not None:
            await simulator.stop()

    return app


app = create_app()
