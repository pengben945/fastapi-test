import asyncio
import logging
import os
import random
import time
from datetime import datetime

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
department_merges = meter.create_counter(
    "department_merges_total", description="Department merges"
)
attendance_checkins = meter.create_counter(
    "attendance_checkins_total", description="Attendance check-ins"
)
attendance_anomalies = meter.create_counter(
    "attendance_anomalies_total", description="Attendance anomalies"
)
attendance_resolutions = meter.create_counter(
    "attendance_resolutions_total", description="Attendance anomalies resolved"
)
attendance_stats_requests = meter.create_counter(
    "attendance_stats_requests_total", description="Attendance stats requests"
)
asset_assignments = meter.create_counter(
    "asset_assignments_total", description="Asset assignments"
)
asset_returns = meter.create_counter(
    "asset_returns_total", description="Asset returns"
)
asset_retirements = meter.create_counter(
    "asset_retirements_total", description="Asset retirements"
)
satisfaction_surveys = meter.create_counter(
    "satisfaction_surveys_total", description="Satisfaction surveys submitted"
)
health_declarations = meter.create_counter(
    "health_declarations_total", description="Health declarations submitted"
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
leave_reviews = meter.create_counter(
    "leave_reviews_total", description="Leave reviews"
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
promotion_requests = meter.create_counter(
    "promotion_requests_total", description="Promotion requests"
)
promotion_decisions = meter.create_counter(
    "promotion_decisions_total", description="Promotion decisions"
)
promotion_finalizations = meter.create_counter(
    "promotion_finalizations_total", description="Promotion finalizations"
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
offboarding_cases = meter.create_counter(
    "offboarding_cases_total", description="Offboarding cases created"
)
offboarding_steps = meter.create_counter(
    "offboarding_steps_total", description="Offboarding steps completed"
)
training_enrollments = meter.create_counter(
    "training_enrollments_total", description="Training enrollments"
)
training_completions = meter.create_counter(
    "training_completions_total", description="Training completions"
)
training_exams = meter.create_counter(
    "training_exams_total", description="Training exams submitted"
)
training_exam_results = meter.create_counter(
    "training_exam_results_total", description="Training exam results"
)
travel_requests = meter.create_counter(
    "travel_requests_total", description="Travel requests created"
)
travel_approvals = meter.create_counter(
    "travel_approvals_total", description="Travel approvals"
)
travel_reviews = meter.create_counter(
    "travel_reviews_total", description="Travel reviews"
)


class DepartmentCreate(BaseModel):
    name: str


class DepartmentMergePayload(BaseModel):
    source_department_id: int
    target_department_id: int
    reason: str | None = None


class EmployeeCreate(BaseModel):
    name: str
    department_id: int
    title: str


class AttendancePayload(BaseModel):
    status: str
    note: str | None = None
    timestamp: str | None = None


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


class LeaveReviewPayload(BaseModel):
    verified: bool
    reviewer: str


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


class PromotionRequestPayload(BaseModel):
    employee_id: int
    new_title: str
    effective_date: str
    reason: str | None = None


class PromotionDecisionPayload(BaseModel):
    approved: bool
    approver: str


class PromotionFinalizePayload(BaseModel):
    hr_reviewer: str


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


class OffboardingCreatePayload(BaseModel):
    employee_id: int
    last_workday: str
    reason: str
    manager: str


class OffboardingStepPayload(BaseModel):
    step: str
    completed: bool = True
    note: str | None = None


class OffboardingFinalizePayload(BaseModel):
    hr_reviewer: str


class TrainingCreatePayload(BaseModel):
    name: str
    capacity: int
    trainer: str


class TrainingEnrollPayload(BaseModel):
    employee_id: int
    status: str | None = None


class TrainingCompletePayload(BaseModel):
    employee_id: int
    score: int


class TrainingExamPayload(BaseModel):
    employee_id: int
    score: int


class TravelRequestCreatePayload(BaseModel):
    employee_id: int
    destination: str
    days: int
    reason: str | None = None


class TravelDecisionPayload(BaseModel):
    approved: bool
    approver: str


class TravelReviewPayload(BaseModel):
    verified: bool
    reviewer: str


class AttendanceAnomalyCreatePayload(BaseModel):
    employee_id: int
    anomaly_type: str
    note: str | None = None


class AttendanceAnomalyResolvePayload(BaseModel):
    resolution: str


class AssetCreatePayload(BaseModel):
    asset_type: str
    serial_number: str
    model: str | None = None


class AssetAssignPayload(BaseModel):
    employee_id: int
    note: str | None = None


class AssetReturnPayload(BaseModel):
    condition: str
    note: str | None = None


class AssetRetirePayload(BaseModel):
    reason: str


class SatisfactionSurveyPayload(BaseModel):
    employee_id: int
    score: int
    comment: str | None = None
    category: str | None = None


class HealthDeclarationPayload(BaseModel):
    employee_id: int
    temperature: float
    symptoms: list[str] = []
    risk_level: str
    note: str | None = None


def create_app() -> FastAPI:
    setup_logging()
    setup_telemetry(SERVICE_NAME)

    app = FastAPI(title="LogPulse HR", version="0.2.0")
    FastAPIInstrumentor.instrument_app(app)
    app.state.simulator = None
    app.state.departments = {}
    app.state.employees = {}
    app.state.attendance = []
    app.state.attendance_anomalies = {}
    app.state.assets = {}
    app.state.satisfaction_surveys = []
    app.state.health_declarations = []
    app.state.leave_requests = {}
    app.state.travel_requests = {}
    app.state.performance_reviews = {}
    app.state.salary_adjustments = {}
    app.state.onboarding_cases = {}
    app.state.offboarding_cases = {}
    app.state.trainings = {}
    app.state.next_department_id = 1
    app.state.next_employee_id = 1000
    app.state.promotion_requests = {}
    app.state.next_promotion_id = 1
    app.state.next_leave_id = 1
    app.state.next_travel_id = 1
    app.state.next_review_id = 1
    app.state.next_salary_id = 1
    app.state.next_onboarding_id = 1
    app.state.next_offboarding_id = 1
    app.state.next_training_id = 1
    app.state.next_anomaly_id = 1
    app.state.next_asset_id = 1

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
        return {"status": "ok", "service": SERVICE_NAME, "version": "1.1.0"}

    @app.get("/stats")
    async def get_system_stats() -> dict[str, int | dict]:
        """获取系统统计信息"""
        # 基础统计
        total_departments = len(app.state.departments)
        total_employees = len(app.state.employees)
        
        # 请假统计
        total_leave_requests = len(app.state.leave_requests)
        approved_leaves = sum(1 for req in app.state.leave_requests.values() if req.get("status") == "approved")
        pending_leaves = sum(1 for req in app.state.leave_requests.values() if req.get("status") == "pending")
        
        # 晋升统计
        total_promotion_requests = len(app.state.promotion_requests)
        finalized_promotions = sum(1 for req in app.state.promotion_requests.values() if req.get("hr_reviewer"))
        
        # 薪资调整统计
        total_salary_requests = len(app.state.salary_requests)
        approved_salary_adjustments = sum(1 for req in app.state.salary_requests.values() if req.get("status") == "approved")
        
        # 入职/离职统计
        total_onboarding = len(app.state.onboarding_cases)
        completed_onboarding = sum(1 for case in app.state.onboarding_cases.values() if case.get("status") == "completed")
        total_offboarding = len(app.state.offboarding_cases)
        completed_offboarding = sum(1 for case in app.state.offboarding_cases.values() if case.get("status") == "completed")
        
        # 培训统计
        total_trainings = len(app.state.trainings)
        total_training_enrollments = len(app.state.training_enrollments)
        
        logger.info("system stats retrieved")
        
        return {
            "organization": {
                "departments": total_departments,
                "employees": total_employees,
            },
            "leave_management": {
                "total_requests": total_leave_requests,
                "approved": approved_leaves,
                "pending": pending_leaves,
            },
            "promotions": {
                "total_requests": total_promotion_requests,
                "finalized": finalized_promotions,
            },
            "salary_adjustments": {
                "total_requests": total_salary_requests,
                "approved": approved_salary_adjustments,
            },
            "onboarding": {
                "total_cases": total_onboarding,
                "completed": completed_onboarding,
            },
            "offboarding": {
                "total_cases": total_offboarding,
                "completed": completed_offboarding,
            },
            "training": {
                "total_courses": total_trainings,
                "total_enrollments": total_training_enrollments,
            },
        }

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

    @app.post("/departments/merge")
    async def merge_departments(
        payload: DepartmentMergePayload,
    ) -> dict[str, int | str | list]:
        if payload.source_department_id == payload.target_department_id:
            raise HTTPException(status_code=400, detail="departments must differ")
        source = app.state.departments.get(payload.source_department_id)
        target = app.state.departments.get(payload.target_department_id)
        if not source or not target:
            raise HTTPException(status_code=404, detail="department not found")
        moved_employees = []
        for employee in app.state.employees.values():
            if employee["department_id"] == payload.source_department_id:
                employee["department_id"] = payload.target_department_id
                moved_employees.append(employee["id"])
        app.state.departments.pop(payload.source_department_id, None)
        department_merges.add(1, {"target_department_id": str(payload.target_department_id)})
        logger.info(
            "department merge source=%s target=%s moved=%s reason=%s",
            payload.source_department_id,
            payload.target_department_id,
            len(moved_employees),
            payload.reason or "",
        )
        return {
            "source_department_id": payload.source_department_id,
            "target_department_id": payload.target_department_id,
            "moved_employees": moved_employees,
        }

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

    @app.post("/promotions/requests")
    async def create_promotion_request(
        payload: PromotionRequestPayload,
    ) -> dict[str, int | str | list]:
        employee = app.state.employees.get(payload.employee_id)
        if not employee:
            raise HTTPException(status_code=404, detail="employee not found")
        if not payload.new_title.strip():
            raise HTTPException(status_code=400, detail="invalid title")
        if not payload.effective_date or len(payload.effective_date) != 10:
            raise HTTPException(status_code=400, detail="invalid effective date")
        request_id = app.state.next_promotion_id
        app.state.next_promotion_id += 1
        record = {
            "id": request_id,
            "employee_id": payload.employee_id,
            "from_title": employee["title"],
            "to_title": payload.new_title,
            "effective_date": payload.effective_date,
            "reason": payload.reason,
            "status": "pending",
            "approver": None,
            "hr_reviewer": None,
            "history": [
                {
                    "action": "created",
                    "at": time.time(),
                }
            ],
        }
        app.state.promotion_requests[request_id] = record
        promotion_requests.add(1, {"department_id": str(employee["department_id"])})
        logger.info(
            "promotion request created id=%s employee_id=%s to_title=%s",
            request_id,
            payload.employee_id,
            payload.new_title,
        )
        return record

    @app.post("/promotions/requests/{request_id}/decision")
    async def decide_promotion_request(
        request_id: int, payload: PromotionDecisionPayload
    ) -> dict[str, int | str | list]:
        record = app.state.promotion_requests.get(request_id)
        if not record:
            raise HTTPException(status_code=404, detail="promotion request not found")
        if record["status"] != "pending":
            raise HTTPException(status_code=409, detail="promotion request already decided")
        status = "approved" if payload.approved else "rejected"
        record["status"] = status
        record["approver"] = payload.approver
        record["history"].append(
            {"action": "decision", "status": status, "at": time.time()}
        )
        promotion_decisions.add(1, {"status": status})
        logger.info(
            "promotion request %s id=%s approver=%s",
            status,
            request_id,
            payload.approver,
        )
        return record

    @app.post("/promotions/requests/{request_id}/finalize")
    async def finalize_promotion_request(
        request_id: int, payload: PromotionFinalizePayload
    ) -> dict[str, int | str | list]:
        record = app.state.promotion_requests.get(request_id)
        if not record:
            raise HTTPException(status_code=404, detail="promotion request not found")
        if record["status"] != "approved":
            raise HTTPException(status_code=409, detail="promotion not approved")
        if record["hr_reviewer"]:
            raise HTTPException(status_code=409, detail="promotion already finalized")
        employee = app.state.employees.get(record["employee_id"])
        if not employee:
            raise HTTPException(status_code=404, detail="employee not found")
        employee["title"] = record["to_title"]
        record["hr_reviewer"] = payload.hr_reviewer
        record["history"].append(
            {"action": "finalized", "at": time.time(), "reviewer": payload.hr_reviewer}
        )
        promotion_finalizations.add(1, {"department_id": str(employee["department_id"])})
        logger.info(
            "promotion finalized id=%s employee_id=%s reviewer=%s",
            request_id,
            record["employee_id"],
            payload.hr_reviewer,
        )
        return record

    @app.get("/promotions/requests/{request_id}")
    async def get_promotion_request(
        request_id: int,
    ) -> dict[str, int | str | list]:
        record = app.state.promotion_requests.get(request_id)
        if not record:
            raise HTTPException(status_code=404, detail="promotion request not found")
        return record

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

    @app.post("/offboarding/cases")
    async def create_offboarding_case(
        payload: OffboardingCreatePayload,
    ) -> dict[str, int | str | list]:
        employee = app.state.employees.get(payload.employee_id)
        if not employee:
            raise HTTPException(status_code=404, detail="employee not found")
        if not payload.last_workday or len(payload.last_workday) != 10:
            raise HTTPException(status_code=400, detail="invalid last workday")
        reason = payload.reason.strip().lower()
        if reason not in {"resignation", "termination", "retirement"}:
            raise HTTPException(status_code=400, detail="invalid offboarding reason")
        steps = [
            {"name": "knowledge_transfer", "completed": False},
            {"name": "account_deactivation", "completed": False},
            {"name": "asset_return", "completed": False},
            {"name": "exit_interview", "completed": False},
        ]
        case_id = app.state.next_offboarding_id
        app.state.next_offboarding_id += 1
        record = {
            "id": case_id,
            "employee_id": payload.employee_id,
            "last_workday": payload.last_workday,
            "reason": reason,
            "manager": payload.manager,
            "status": "in_progress",
            "steps": steps,
            "notes": [],
            "created_at": time.time(),
        }
        app.state.offboarding_cases[case_id] = record
        offboarding_cases.add(1, {"reason": reason})
        logger.info(
            "offboarding case created id=%s employee_id=%s reason=%s",
            case_id,
            payload.employee_id,
            reason,
        )
        return record

    @app.post("/offboarding/cases/{case_id}/steps")
    async def complete_offboarding_step(
        case_id: int, payload: OffboardingStepPayload
    ) -> dict[str, int | str | list]:
        record = app.state.offboarding_cases.get(case_id)
        if not record:
            raise HTTPException(status_code=404, detail="offboarding case not found")
        step = payload.step.strip().lower()
        for item in record["steps"]:
            if item["name"] == step:
                item["completed"] = payload.completed
                if payload.note:
                    record["notes"].append(
                        {"step": step, "note": payload.note, "at": time.time()}
                    )
                offboarding_steps.add(1, {"step": step})
                logger.info(
                    "offboarding step updated case_id=%s step=%s completed=%s",
                    case_id,
                    step,
                    payload.completed,
                )
                return record
        raise HTTPException(status_code=404, detail="step not found")

    @app.post("/offboarding/cases/{case_id}/finalize")
    async def finalize_offboarding(
        case_id: int, payload: OffboardingFinalizePayload
    ) -> dict[str, int | str | list]:
        record = app.state.offboarding_cases.get(case_id)
        if not record:
            raise HTTPException(status_code=404, detail="offboarding case not found")
        if record["status"] != "in_progress":
            raise HTTPException(status_code=409, detail="offboarding already finalized")
        if not all(step["completed"] for step in record["steps"]):
            raise HTTPException(status_code=400, detail="steps not completed")
        record["status"] = "completed"
        record["hr_reviewer"] = payload.hr_reviewer
        record["completed_at"] = time.time()
        logger.info(
            "offboarding finalized case_id=%s reviewer=%s",
            case_id,
            payload.hr_reviewer,
        )
        return record

    @app.post("/trainings")
    async def create_training(payload: TrainingCreatePayload) -> dict[str, int | str]:
        if not payload.name.strip():
            raise HTTPException(status_code=400, detail="invalid training name")
        if payload.capacity <= 0:
            raise HTTPException(status_code=400, detail="invalid capacity")
        training_id = app.state.next_training_id
        app.state.next_training_id += 1
        record = {
            "id": training_id,
            "name": payload.name,
            "capacity": payload.capacity,
            "trainer": payload.trainer,
            "enrolled": [],
            "completed": [],
            "exams": {},
            "created_at": time.time(),
        }
        app.state.trainings[training_id] = record
        logger.info("training created id=%s name=%s", training_id, payload.name)
        return record

    @app.post("/trainings/{training_id}/enroll")
    async def enroll_training(
        training_id: int, payload: TrainingEnrollPayload
    ) -> dict[str, int | str | list]:
        training = app.state.trainings.get(training_id)
        if not training:
            raise HTTPException(status_code=404, detail="training not found")
        if payload.employee_id not in app.state.employees:
            raise HTTPException(status_code=404, detail="employee not found")
        if payload.employee_id in training["enrolled"]:
            raise HTTPException(status_code=409, detail="already enrolled")
        if len(training["enrolled"]) >= training["capacity"]:
            raise HTTPException(status_code=409, detail="training is full")
        status = (payload.status or "registered").strip().lower()
        training["enrolled"].append(payload.employee_id)
        training_enrollments.add(1, {"training": training["name"], "status": status})
        logger.info(
            "training enrolled training_id=%s employee_id=%s",
            training_id,
            payload.employee_id,
        )
        return training

    @app.post("/trainings/{training_id}/exam")
    async def submit_training_exam(
        training_id: int, payload: TrainingExamPayload
    ) -> dict[str, int | str | list]:
        training = app.state.trainings.get(training_id)
        if not training:
            raise HTTPException(status_code=404, detail="training not found")
        if payload.employee_id not in training["enrolled"]:
            raise HTTPException(status_code=409, detail="not enrolled")
        if payload.score < 0 or payload.score > 100:
            raise HTTPException(status_code=400, detail="invalid score")
        passed = payload.score >= 60
        training["exams"][payload.employee_id] = {
            "score": payload.score,
            "passed": passed,
            "submitted_at": time.time(),
        }
        training_exams.add(1, {"training": training["name"]})
        training_exam_results.add(1, {"training": training["name"], "passed": str(passed)})
        logger.info(
            "training exam submitted training_id=%s employee_id=%s passed=%s",
            training_id,
            payload.employee_id,
            passed,
        )
        return training

    @app.post("/trainings/{training_id}/complete")
    async def complete_training(
        training_id: int, payload: TrainingCompletePayload
    ) -> dict[str, int | str | list]:
        training = app.state.trainings.get(training_id)
        if not training:
            raise HTTPException(status_code=404, detail="training not found")
        if payload.employee_id not in training["enrolled"]:
            raise HTTPException(status_code=409, detail="not enrolled")
        exam = training["exams"].get(payload.employee_id)
        if not exam or not exam["passed"]:
            raise HTTPException(status_code=400, detail="exam not passed")
        if payload.score < 0 or payload.score > 100:
            raise HTTPException(status_code=400, detail="invalid score")
        if payload.employee_id in training["completed"]:
            raise HTTPException(status_code=409, detail="already completed")
        training["completed"].append(payload.employee_id)
        training_completions.add(1, {"training": training["name"]})
        logger.info(
            "training completed training_id=%s employee_id=%s score=%s",
            training_id,
            payload.employee_id,
            payload.score,
        )
        return training

    @app.post("/travel/requests")
    async def create_travel_request(
        payload: TravelRequestCreatePayload,
    ) -> dict[str, int | str]:
        if payload.employee_id not in app.state.employees:
            raise HTTPException(status_code=404, detail="employee not found")
        if payload.days <= 0:
            raise HTTPException(status_code=400, detail="invalid travel days")
        if not payload.destination.strip():
            raise HTTPException(status_code=400, detail="invalid destination")
        request_id = app.state.next_travel_id
        app.state.next_travel_id += 1
        record = {
            "id": request_id,
            "employee_id": payload.employee_id,
            "destination": payload.destination,
            "days": payload.days,
            "reason": payload.reason,
            "status": "pending",
            "approver": None,
            "reviewer": None,
            "created_at": time.time(),
        }
        app.state.travel_requests[request_id] = record
        travel_requests.add(1, {"destination": payload.destination})
        logger.info(
            "travel request created id=%s employee_id=%s destination=%s",
            request_id,
            payload.employee_id,
            payload.destination,
        )
        return record
        

    @app.post("/travel/requests/{request_id}/decision")
    async def decide_travel(
        request_id: int, payload: TravelDecisionPayload
    ) -> dict[str, int | str]:
        record = app.state.travel_requests.get(request_id)
        if not record:
            raise HTTPException(status_code=404, detail="travel request not found")
        if record["status"] != "pending":
            raise HTTPException(status_code=409, detail="travel request already decided")
        status = "approved" if payload.approved else "rejected"
        record["status"] = status
        record["approver"] = payload.approver
        record["decided_at"] = time.time()
        travel_approvals.add(1, {"status": status})
        logger.info(
            "travel request %s id=%s approver=%s", status, request_id, payload.approver
        )
        return record

    @app.post("/travel/requests/{request_id}/review")
    async def review_travel(
        request_id: int, payload: TravelReviewPayload
    ) -> dict[str, int | str]:
        record = app.state.travel_requests.get(request_id)
        if not record:
            raise HTTPException(status_code=404, detail="travel request not found")
        if record["status"] != "approved":
            raise HTTPException(status_code=409, detail="travel request not approved")
        if record.get("reviewed_at"):
            raise HTTPException(status_code=409, detail="travel request already reviewed")
        record["reviewed_at"] = time.time()
        record["reviewer"] = payload.reviewer
        record["review_status"] = "verified" if payload.verified else "recheck"
        travel_reviews.add(1, {"review_status": record["review_status"]})
        logger.info(
            "travel review id=%s status=%s reviewer=%s",
            request_id,
            record["review_status"],
            payload.reviewer,
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
        event_time = time.time()
        if payload.timestamp:
            try:
                cleaned = payload.timestamp.replace("Z", "+00:00")
                parsed = datetime.fromisoformat(cleaned)
                event_time = parsed.timestamp()
            except ValueError:
                raise HTTPException(status_code=400, detail="invalid timestamp") from None
        if event_time > time.time() + 300:
            raise HTTPException(status_code=400, detail="timestamp in future")
        if event_time < time.time() - 86400:
            raise HTTPException(status_code=400, detail="timestamp too old")
        last_record = next(
            (rec for rec in reversed(app.state.attendance) if rec["employee_id"] == employee_id),
            None,
        )
        if last_record and last_record["status"] == status:
            raise HTTPException(status_code=409, detail="duplicate attendance status")
        record = {
            "employee_id": employee_id,
            "status": status,
            "note": payload.note,
            "ts": event_time,
        }
        app.state.attendance.append(record)
        attendance_checkins.add(1, {"status": status})
        logger.info("attendance %s employee_id=%s note=%s", status, employee_id, payload.note or "")
        return {"status": "ok"}

    @app.post("/attendance/anomalies")
    async def create_attendance_anomaly(
        payload: AttendanceAnomalyCreatePayload,
    ) -> dict[str, int | str]:
        if payload.employee_id not in app.state.employees:
            raise HTTPException(status_code=404, detail="employee not found")
        anomaly_type = payload.anomaly_type.strip().lower()
        if anomaly_type not in {"late", "missing_checkout", "no_show"}:
            raise HTTPException(status_code=400, detail="invalid anomaly type")
        anomaly_id = app.state.next_anomaly_id
        app.state.next_anomaly_id += 1
        record = {
            "id": anomaly_id,
            "employee_id": payload.employee_id,
            "anomaly_type": anomaly_type,
            "note": payload.note,
            "status": "open",
            "created_at": time.time(),
            "resolution": None,
            "resolved_at": None,
        }
        app.state.attendance_anomalies[anomaly_id] = record
        attendance_anomalies.add(1, {"type": anomaly_type})
        logger.info(
            "attendance anomaly created id=%s employee_id=%s type=%s",
            anomaly_id,
            payload.employee_id,
            anomaly_type,
        )
        return record

    @app.post("/attendance/anomalies/{anomaly_id}/resolve")
    async def resolve_attendance_anomaly(
        anomaly_id: int, payload: AttendanceAnomalyResolvePayload
    ) -> dict[str, int | str]:
        record = app.state.attendance_anomalies.get(anomaly_id)
        if not record:
            raise HTTPException(status_code=404, detail="anomaly not found")
        if record["status"] != "open":
            raise HTTPException(status_code=409, detail="anomaly already resolved")
        record["status"] = "resolved"
        record["resolution"] = payload.resolution
        record["resolved_at"] = time.time()
        attendance_resolutions.add(1, {"type": record["anomaly_type"]})
        logger.info(
            "attendance anomaly resolved id=%s resolution=%s",
            anomaly_id,
            payload.resolution,
        )
        return record

    @app.get("/attendance/stats")
    async def attendance_stats() -> dict[str, int]:
        total = len(app.state.attendance)
        total_in = sum(1 for record in app.state.attendance if record["status"] == "in")
        total_out = sum(1 for record in app.state.attendance if record["status"] == "out")
        open_anomalies = sum(
            1 for record in app.state.attendance_anomalies.values() if record["status"] == "open"
        )
        resolved_anomalies = sum(
            1
            for record in app.state.attendance_anomalies.values()
            if record["status"] == "resolved"
        )
        attendance_stats_requests.add(1, {})
        logger.info("attendance stats total=%s open=%s", total, open_anomalies)
        return {
            "total": total,
            "checkins": total_in,
            "checkouts": total_out,
            "open_anomalies": open_anomalies,
            "resolved_anomalies": resolved_anomalies,
        }

    @app.post("/assets")
    async def create_asset(payload: AssetCreatePayload) -> dict[str, int | str | None]:
        asset_type = payload.asset_type.strip().lower()
        if asset_type not in {"laptop", "desktop", "phone"}:
            raise HTTPException(status_code=400, detail="invalid asset type")
        if not payload.serial_number.strip():
            raise HTTPException(status_code=400, detail="invalid serial number")
        asset_id = app.state.next_asset_id
        app.state.next_asset_id += 1
        record = {
            "id": asset_id,
            "asset_type": asset_type,
            "serial_number": payload.serial_number,
            "model": payload.model,
            "status": "available",
            "assigned_to": None,
            "history": [],
        }
        app.state.assets[asset_id] = record
        logger.info("asset created id=%s type=%s", asset_id, asset_type)
        return record

    @app.post("/assets/{asset_id}/assign")
    async def assign_asset(
        asset_id: int, payload: AssetAssignPayload
    ) -> dict[str, int | str | None | list]:
        asset = app.state.assets.get(asset_id)
        if not asset:
            raise HTTPException(status_code=404, detail="asset not found")
        if asset["status"] != "available":
            raise HTTPException(status_code=409, detail="asset not available")
        if payload.employee_id not in app.state.employees:
            raise HTTPException(status_code=404, detail="employee not found")
        asset["status"] = "assigned"
        asset["assigned_to"] = payload.employee_id
        asset["history"].append(
            {
                "action": "assigned",
                "employee_id": payload.employee_id,
                "note": payload.note,
                "at": time.time(),
            }
        )
        asset_assignments.add(1, {"asset_type": asset["asset_type"]})
        logger.info(
            "asset assigned id=%s employee_id=%s", asset_id, payload.employee_id
        )
        return asset

    @app.post("/assets/{asset_id}/return")
    async def return_asset(
        asset_id: int, payload: AssetReturnPayload
    ) -> dict[str, int | str | None | list]:
        asset = app.state.assets.get(asset_id)
        if not asset:
            raise HTTPException(status_code=404, detail="asset not found")
        if asset["status"] != "assigned":
            raise HTTPException(status_code=409, detail="asset not assigned")
        asset["status"] = "available"
        asset["history"].append(
            {
                "action": "returned",
                "employee_id": asset["assigned_to"],
                "condition": payload.condition,
                "note": payload.note,
                "at": time.time(),
            }
        )
        asset["assigned_to"] = None
        asset_returns.add(1, {"condition": payload.condition})
        logger.info("asset returned id=%s condition=%s", asset_id, payload.condition)
        return asset

    @app.post("/assets/{asset_id}/retire")
    async def retire_asset(
        asset_id: int, payload: AssetRetirePayload
    ) -> dict[str, int | str | None | list]:
        asset = app.state.assets.get(asset_id)
        if not asset:
            raise HTTPException(status_code=404, detail="asset not found")
        if asset["status"] == "retired":
            raise HTTPException(status_code=409, detail="asset already retired")
        if asset["status"] == "assigned":
            raise HTTPException(status_code=409, detail="asset assigned to employee")
        asset["status"] = "retired"
        asset["history"].append(
            {"action": "retired", "reason": payload.reason, "at": time.time()}
        )
        asset_retirements.add(1, {"asset_type": asset["asset_type"]})
        logger.info("asset retired id=%s reason=%s", asset_id, payload.reason)
        return asset

    @app.post("/surveys/satisfaction")
    async def submit_satisfaction_survey(
        payload: SatisfactionSurveyPayload,
    ) -> dict[str, int | str]:
        if payload.employee_id not in app.state.employees:
            raise HTTPException(status_code=404, detail="employee not found")
        if payload.score < 1 or payload.score > 5:
            raise HTTPException(status_code=400, detail="invalid score")
        category = (payload.category or "general").strip().lower()
        record = {
            "employee_id": payload.employee_id,
            "score": payload.score,
            "comment": payload.comment,
            "category": category,
            "created_at": time.time(),
        }
        app.state.satisfaction_surveys.append(record)
        satisfaction_surveys.add(1, {"category": category, "score": str(payload.score)})
        logger.info(
            "satisfaction survey employee_id=%s score=%s category=%s",
            payload.employee_id,
            payload.score,
            category,
        )
        return {"status": "ok"}

    @app.post("/health/declarations")
    async def submit_health_declaration(
        payload: HealthDeclarationPayload,
    ) -> dict[str, int | str]:
        if payload.employee_id not in app.state.employees:
            raise HTTPException(status_code=404, detail="employee not found")
        if payload.temperature < 34 or payload.temperature > 42:
            raise HTTPException(status_code=400, detail="invalid temperature")
        risk = payload.risk_level.strip().lower()
        if risk not in {"low", "medium", "high"}:
            raise HTTPException(status_code=400, detail="invalid risk level")
        record = {
            "employee_id": payload.employee_id,
            "temperature": payload.temperature,
            "symptoms": payload.symptoms,
            "risk_level": risk,
            "note": payload.note,
            "created_at": time.time(),
        }
        app.state.health_declarations.append(record)
        health_declarations.add(1, {"risk_level": risk})
        logger.info(
            "health declaration employee_id=%s temp=%.1f risk=%s",
            payload.employee_id,
            payload.temperature,
            risk,
        )
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

    @app.post("/leave/requests/{leave_id}/review")
    async def review_leave(leave_id: int, payload: LeaveReviewPayload) -> dict[str, int | str]:
        record = app.state.leave_requests.get(leave_id)
        if not record:
            raise HTTPException(status_code=404, detail="leave request not found")
        if record["status"] != "approved":
            raise HTTPException(status_code=409, detail="leave request not approved")
        if record.get("reviewed_at"):
            raise HTTPException(status_code=409, detail="leave request already reviewed")
        record["reviewed_at"] = time.time()
        record["reviewer"] = payload.reviewer
        record["review_status"] = "verified" if payload.verified else "recheck"
        leave_reviews.add(1, {"review_status": record["review_status"]})
        logger.info(
            "leave review id=%s status=%s reviewer=%s",
            leave_id,
            record["review_status"],
            payload.reviewer,
        )
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
