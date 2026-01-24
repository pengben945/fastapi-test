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
promotions = meter.create_counter(
    "employee_promotions_total", description="Employee promotions"
)
salary_requests = meter.create_counter(
    "salary_adjust_requests_total", description="Salary adjustment requests"
)
salary_decisions = meter.create_counter(
    "salary_adjust_decisions_total", description="Salary adjustment decisions"
)
onboarding_cases = meter.create_counter(
    "onboarding_cases_total", description="Onboarding cases created"
)
onboarding_steps = meter.create_counter(
    "onboarding_steps_total", description="Onboarding steps completed"
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


class DepartmentTransferPayload(BaseModel):
    department_id: int
    reason: str | None = None


class PromotionPayload(BaseModel):
    new_title: str
    effective_date: str
    reason: str | None = None


class SalaryAdjustRequestPayload(BaseModel):
    employee_id: int
    current_salary: float
    proposed_salary: float
    effective_date: str
    reason: str | None = None


class SalaryAdjustDecisionPayload(BaseModel):
    approved: bool
    approver: str
    level: str


class OnboardingCreatePayload(BaseModel):
    employee_id: int
    start_date: str
    equipment: str
    buddy: str | None = None


class OnboardingStepPayload(BaseModel):
    step: str
    completed: bool = True
    note: str | None = None


class OnboardingFinalizePayload(BaseModel):
    hr_reviewer: str


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
    app.state.salary_adjustments = {}
    app.state.onboarding_cases = {}
    app.state.next_department_id = 1
    app.state.next_employee_id = 1000
    app.state.next_leave_id = 1
    app.state.next_review_id = 1
    app.state.next_salary_id = 1
    app.state.next_onboarding_id = 1

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

    @app.post("/employees/{employee_id}/transfer")
    async def transfer_employee(
        employee_id: int, payload: DepartmentTransferPayload
    ) -> dict[str, int | str]:
        employee = app.state.employees.get(employee_id)
        if not employee:
            raise HTTPException(status_code=404, detail="employee not found")
        if payload.department_id not in app.state.departments:
            raise HTTPException(status_code=404, detail="department not found")
        if employee["department_id"] == payload.department_id:
            raise HTTPException(status_code=409, detail="already in department")
        old_department = employee["department_id"]
        employee["department_id"] = payload.department_id
        logger.info(
            "department transfer employee_id=%s from=%s to=%s reason=%s",
            employee_id,
            old_department,
            payload.department_id,
            payload.reason or "",
        )
        return employee

    @app.post("/employees/{employee_id}/promotion")
    async def promote_employee(
        employee_id: int, payload: PromotionPayload
    ) -> dict[str, int | str]:
        employee = app.state.employees.get(employee_id)
        if not employee:
            raise HTTPException(status_code=404, detail="employee not found")
        if not payload.new_title.strip():
            raise HTTPException(status_code=400, detail="invalid title")
        if not payload.effective_date or len(payload.effective_date) != 10:
            raise HTTPException(status_code=400, detail="invalid effective date")
        old_title = employee["title"]
        employee["title"] = payload.new_title
        promotions.add(1, {"department_id": str(employee["department_id"])})
        logger.info(
            "promotion employee_id=%s from=%s to=%s effective_date=%s",
            employee_id,
            old_title,
            payload.new_title,
            payload.effective_date,
        )
        return employee

    @app.post("/salary/adjustments")
    async def create_salary_adjustment(
        payload: SalaryAdjustRequestPayload,
    ) -> dict[str, int | str | float]:
        if payload.employee_id not in app.state.employees:
            raise HTTPException(status_code=404, detail="employee not found")
        if payload.current_salary <= 0 or payload.proposed_salary <= 0:
            raise HTTPException(status_code=400, detail="invalid salary")
        if payload.proposed_salary == payload.current_salary:
            raise HTTPException(status_code=400, detail="no change in salary")
        if not payload.effective_date or len(payload.effective_date) != 10:
            raise HTTPException(status_code=400, detail="invalid effective date")
        change_ratio = (payload.proposed_salary - payload.current_salary) / payload.current_salary
        approval_level = "hr"
        if change_ratio >= 0.2:
            approval_level = "director"
        elif change_ratio >= 0.1:
            approval_level = "manager"
        request_id = app.state.next_salary_id
        app.state.next_salary_id += 1
        record = {
            "id": request_id,
            "employee_id": payload.employee_id,
            "current_salary": payload.current_salary,
            "proposed_salary": payload.proposed_salary,
            "effective_date": payload.effective_date,
            "reason": payload.reason,
            "status": "pending",
            "required_level": approval_level,
            "approvals": [],
            "created_at": time.time(),
        }
        app.state.salary_adjustments[request_id] = record
        salary_requests.add(1, {"required_level": approval_level})
        logger.info(
            "salary request created id=%s employee_id=%s level=%s",
            request_id,
            payload.employee_id,
            approval_level,
        )
        return record

    @app.post("/salary/adjustments/{request_id}/decision")
    async def decide_salary_adjustment(
        request_id: int, payload: SalaryAdjustDecisionPayload
    ) -> dict[str, int | str | float]:
        record = app.state.salary_adjustments.get(request_id)
        if not record:
            raise HTTPException(status_code=404, detail="salary request not found")
        if record["status"] != "pending":
            raise HTTPException(status_code=409, detail="salary request already decided")
        level = payload.level.strip().lower()
        if level not in {"hr", "manager", "director"}:
            raise HTTPException(status_code=400, detail="invalid approval level")
        record["approvals"].append(
            {
                "approver": payload.approver,
                "level": level,
                "approved": payload.approved,
                "at": time.time(),
            }
        )
        if not payload.approved:
            record["status"] = "rejected"
        else:
            required_level = record["required_level"]
            order = ["hr", "manager", "director"]
            if order.index(level) >= order.index(required_level):
                record["status"] = "approved"
        salary_decisions.add(1, {"status": record["status"], "level": level})
        logger.info(
            "salary decision request_id=%s status=%s level=%s",
            request_id,
            record["status"],
            level,
        )
        return record

    @app.post("/onboarding/cases")
    async def create_onboarding_case(
        payload: OnboardingCreatePayload,
    ) -> dict[str, int | str | list]:
        if payload.employee_id not in app.state.employees:
            raise HTTPException(status_code=404, detail="employee not found")
        if not payload.start_date or len(payload.start_date) != 10:
            raise HTTPException(status_code=400, detail="invalid start date")
        if not payload.equipment.strip():
            raise HTTPException(status_code=400, detail="invalid equipment")
        onboarding_id = app.state.next_onboarding_id
        app.state.next_onboarding_id += 1
        steps = [
            {"name": "account_setup", "completed": False},
            {"name": "equipment_handover", "completed": False},
            {"name": "policy_briefing", "completed": False},
            {"name": "security_training", "completed": False},
        ]
        record = {
            "id": onboarding_id,
            "employee_id": payload.employee_id,
            "start_date": payload.start_date,
            "equipment": payload.equipment,
            "buddy": payload.buddy,
            "status": "in_progress",
            "steps": steps,
            "notes": [],
            "created_at": time.time(),
        }
        app.state.onboarding_cases[onboarding_id] = record
        onboarding_cases.add(1, {"equipment": payload.equipment})
        logger.info(
            "onboarding case created id=%s employee_id=%s start_date=%s",
            onboarding_id,
            payload.employee_id,
            payload.start_date,
        )
        return record

    @app.post("/onboarding/cases/{case_id}/steps")
    async def complete_onboarding_step(
        case_id: int, payload: OnboardingStepPayload
    ) -> dict[str, int | str | list]:
        record = app.state.onboarding_cases.get(case_id)
        if not record:
            raise HTTPException(status_code=404, detail="onboarding case not found")
        step = payload.step.strip().lower()
        for item in record["steps"]:
            if item["name"] == step:
                item["completed"] = payload.completed
                if payload.note:
                    record["notes"].append(
                        {"step": step, "note": payload.note, "at": time.time()}
                    )
                onboarding_steps.add(1, {"step": step})
                logger.info(
                    "onboarding step updated case_id=%s step=%s completed=%s",
                    case_id,
                    step,
                    payload.completed,
                )
                return record
        raise HTTPException(status_code=404, detail="step not found")

    @app.post("/onboarding/cases/{case_id}/finalize")
    async def finalize_onboarding(
        case_id: int, payload: OnboardingFinalizePayload
    ) -> dict[str, int | str | list]:
        record = app.state.onboarding_cases.get(case_id)
        if not record:
            raise HTTPException(status_code=404, detail="onboarding case not found")
        if record["status"] != "in_progress":
            raise HTTPException(status_code=409, detail="onboarding already finalized")
        if not all(step["completed"] for step in record["steps"]):
            raise HTTPException(status_code=400, detail="steps not completed")
        record["status"] = "completed"
        record["hr_reviewer"] = payload.hr_reviewer
        record["completed_at"] = time.time()
        logger.info(
            "onboarding finalized case_id=%s reviewer=%s", case_id, payload.hr_reviewer
        )
        return record

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
