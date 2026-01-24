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
leave_requests = meter.create_counter(
    "leave_requests_total", description="Leave requests created"
)
leave_approvals = meter.create_counter(
    "leave_approvals_total", description="Leave approvals"
)
performance_reviews = meter.create_counter(
    "performance_reviews_total", description="Performance reviews created"
)
performance_decisions = meter.create_counter(
    "performance_decisions_total", description="Performance review decisions"
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


class LeaveRequestCreate(BaseModel):
    employee_id: int
    leave_type: str
    days: int
    reason: str | None = None


class LeaveDecisionPayload(BaseModel):
    approved: bool
    approver: str


class ReviewCreatePayload(BaseModel):
    employee_id: int
    period: str
    score: int
    summary: str | None = None


class ReviewDecisionPayload(BaseModel):
    final_rating: str
    reviewer: str


def create_app() -> FastAPI:
    setup_logging()
    setup_telemetry(SERVICE_NAME)

    app = FastAPI(title="LogPulse HR", version="0.2.0")
    FastAPIInstrumentor.instrument_app(app)
    app.state.simulator = None
    app.state.departments = {}
    app.state.employees = {}
    app.state.attendance = []
    app.state.leave_requests = {}
    app.state.performance_reviews = {}
    app.state.next_department_id = 1
    app.state.next_employee_id = 1000
    app.state.next_leave_id = 1
    app.state.next_review_id = 1

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

    @app.post("/leave/requests")
    async def create_leave_request(payload: LeaveRequestCreate) -> dict[str, int | str]:
        if payload.employee_id not in app.state.employees:
            raise HTTPException(status_code=404, detail="employee not found")
        if payload.days <= 0:
            raise HTTPException(status_code=400, detail="invalid leave days")
        leave_type = payload.leave_type.strip().lower()
        if leave_type not in {"annual", "sick", "personal"}:
            raise HTTPException(status_code=400, detail="invalid leave type")
        leave_id = app.state.next_leave_id
        app.state.next_leave_id += 1
        record = {
            "id": leave_id,
            "employee_id": payload.employee_id,
            "leave_type": leave_type,
            "days": payload.days,
            "reason": payload.reason,
            "status": "pending",
            "approver": None,
            "created_at": time.time(),
        }
        app.state.leave_requests[leave_id] = record
        leave_requests.add(1, {"leave_type": leave_type})
        logger.info("leave request created id=%s employee_id=%s type=%s", leave_id, payload.employee_id, leave_type)
        return record

    @app.post("/leave/requests/{leave_id}/decision")
    async def decide_leave(leave_id: int, payload: LeaveDecisionPayload) -> dict[str, int | str]:
        record = app.state.leave_requests.get(leave_id)
        if not record:
            raise HTTPException(status_code=404, detail="leave request not found")
        if record["status"] != "pending":
            raise HTTPException(status_code=409, detail="leave request already decided")
        status = "approved" if payload.approved else "rejected"
        record["status"] = status
        record["approver"] = payload.approver
        record["decided_at"] = time.time()
        leave_approvals.add(1, {"status": status})
        logger.info("leave request %s id=%s approver=%s", status, leave_id, payload.approver)
        return record

    @app.post("/performance/reviews")
    async def create_review(payload: ReviewCreatePayload) -> dict[str, int | str]:
        if payload.employee_id not in app.state.employees:
            raise HTTPException(status_code=404, detail="employee not found")
        if payload.score < 1 or payload.score > 5:
            raise HTTPException(status_code=400, detail="invalid score")
        if not payload.period or len(payload.period) != 7 or payload.period[4] != "-":
            raise HTTPException(status_code=400, detail="invalid period format")
        review_id = app.state.next_review_id
        app.state.next_review_id += 1
        record = {
            "id": review_id,
            "employee_id": payload.employee_id,
            "period": payload.period,
            "score": payload.score,
            "summary": payload.summary,
            "status": "submitted",
            "final_rating": None,
            "reviewer": None,
            "created_at": time.time(),
        }
        app.state.performance_reviews[review_id] = record
        performance_reviews.add(1, {"period": payload.period})
        logger.info(
            "performance review created id=%s employee_id=%s period=%s",
            review_id,
            payload.employee_id,
            payload.period,
        )
        return record

    @app.post("/performance/reviews/{review_id}/decision")
    async def decide_review(review_id: int, payload: ReviewDecisionPayload) -> dict[str, int | str]:
        record = app.state.performance_reviews.get(review_id)
        if not record:
            raise HTTPException(status_code=404, detail="review not found")
        if record["status"] != "submitted":
            raise HTTPException(status_code=409, detail="review already decided")
        rating = payload.final_rating.strip().upper()
        if rating not in {"A", "B", "C"}:
            raise HTTPException(status_code=400, detail="invalid rating")
        record["status"] = "finalized"
        record["final_rating"] = rating
        record["reviewer"] = payload.reviewer
        record["decided_at"] = time.time()
        performance_decisions.add(1, {"final_rating": rating})
        logger.info("performance review finalized id=%s rating=%s", review_id, rating)
        return record

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
