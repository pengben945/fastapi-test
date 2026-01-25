import os
from datetime import datetime, timedelta

os.environ["SIM_ENABLED"] = "false"
os.environ["OTEL_SDK_DISABLED"] = "true"

from fastapi.testclient import TestClient

from app.main import create_app


client = TestClient(create_app())


def test_health() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["service"] == "logpulse"
    assert response.json()["version"] == "1.1.0"


def test_department_and_employee_flow() -> None:
    dept = client.post("/departments", json={"name": "Engineering"})
    assert dept.status_code == 200
    department_id = dept.json()["id"]

    employee = client.post(
        "/employees",
        json={"name": "Alice", "department_id": department_id, "title": "Engineer"},
    )
    assert employee.status_code == 200
    employee_id = employee.json()["id"]

    employee_get = client.get(f"/employees/{employee_id}")
    assert employee_get.status_code == 200
    assert employee_get.json()["name"] == "Alice"

def test_attendance_invalid_status() -> None:
    dept = client.post("/departments", json={"name": "HR"})
    employee = client.post(
        "/employees",
        json={"name": "Bob", "department_id": dept.json()["id"], "title": "Manager"},
    )
    response = client.post(
        f"/employees/{employee.json()['id']}/attendance",
        json={"status": "maybe"},
    )
    assert response.status_code == 400


def test_payroll_invalid_month() -> None:
    response = client.post("/payroll/run", json={"month": "2026/01"})
    assert response.status_code == 400


def test_leave_request_and_decision() -> None:
    dept = client.post("/departments", json={"name": "Finance"})
    employee = client.post(
        "/employees",
        json={"name": "Eve", "department_id": dept.json()["id"], "title": "Analyst"},
    )
    leave = client.post(
        "/leave/requests",
        json={
            "employee_id": employee.json()["id"],
            "leave_type": "annual",
            "days": 2,
            "reason": "travel",
        },
    )
    assert leave.status_code == 200
    leave_id = leave.json()["id"]
    decision = client.post(
        f"/leave/requests/{leave_id}/decision",
        json={"approved": True, "approver": "manager_1"},
    )
    assert decision.status_code == 200

    review = client.post(
        f"/leave/requests/{leave_id}/review",
        json={"verified": True, "reviewer": "hr_ops"},
    )
    assert review.status_code == 200


def test_performance_review_flow() -> None:
    dept = client.post("/departments", json={"name": "Sales"})
    employee = client.post(
        "/employees",
        json={"name": "Noah", "department_id": dept.json()["id"], "title": "Sales"},
    )
    review = client.post(
        "/performance/reviews",
        json={
            "employee_id": employee.json()["id"],
            "period": "2026-01",
            "score": 4,
            "summary": "solid",
        },
    )
    assert review.status_code == 200
    review_id = review.json()["id"]
    decision = client.post(
        f"/performance/reviews/{review_id}/decision",
        json={"final_rating": "A", "reviewer": "manager_1"},
    )
    assert decision.status_code == 200


def test_performance_cycle_flow() -> None:
    dept = client.post("/departments", json={"name": "Ops"})
    dept_id = dept.json()["id"]
    employee_1 = client.post(
        "/employees",
        json={"name": "Uma", "department_id": dept_id, "title": "Ops"},
    )
    employee_2 = client.post(
        "/employees",
        json={"name": "Vic", "department_id": dept_id, "title": "Ops"},
    )
    assert employee_1.status_code == 200
    assert employee_2.status_code == 200
    cycle = client.post(
        "/performance/cycles",
        json={
            "period": "2026-01",
            "start_date": "2026-01-01",
            "end_date": "2026-01-31",
            "department_id": dept_id,
            "description": "Ops monthly review",
        },
    )
    assert cycle.status_code == 200
    cycle_id = cycle.json()["id"]
    generated = client.post(f"/performance/cycles/{cycle_id}/generate")
    assert generated.status_code == 200
    assert generated.json()["created_reviews"] >= 2
    cycle_detail = client.get(f"/performance/cycles/{cycle_id}")
    assert cycle_detail.status_code == 200
    assert cycle_detail.json()["total_reviews"] >= 2


def test_performance_cycle_submit_and_close() -> None:
    dept = client.post("/departments", json={"name": "QA"})
    dept_id = dept.json()["id"]
    employee = client.post(
        "/employees",
        json={"name": "Ken", "department_id": dept_id, "title": "QA"},
    )
    cycle = client.post(
        "/performance/cycles",
        json={
            "period": "2026-02",
            "start_date": "2026-02-01",
            "end_date": "2026-02-28",
            "department_id": dept_id,
            "description": "QA monthly review",
        },
    )
    cycle_id = cycle.json()["id"]
    generated = client.post(f"/performance/cycles/{cycle_id}/generate")
    assert generated.status_code == 200

    review_id = None
    for rid, review in client.app.state.performance_reviews.items():
        if review.get("cycle_id") == cycle_id and review["employee_id"] == employee.json()["id"]:
            review_id = rid
            break
    assert review_id is not None

    submit = client.post(
        f"/performance/reviews/{review_id}/submit",
        json={"score": 4, "summary": "steady performance"},
    )
    assert submit.status_code == 200
    decision = client.post(
        f"/performance/reviews/{review_id}/decision",
        json={"final_rating": "A", "reviewer": "lead_1"},
    )
    assert decision.status_code == 200
    close = client.post(f"/performance/cycles/{cycle_id}/close")
    assert close.status_code == 200
    assert close.json()["status"] == "closed"


def test_department_transfer() -> None:
    dept1 = client.post("/departments", json={"name": "Ops"})
    dept2 = client.post("/departments", json={"name": "Support"})
    employee = client.post(
        "/employees",
        json={"name": "Liam", "department_id": dept1.json()["id"], "title": "Agent"},
    )
    transfer = client.post(
        f"/employees/{employee.json()['id']}/transfer",
        json={"department_id": dept2.json()["id"], "reason": "reorg"},
    )
    assert transfer.status_code == 200
    assert transfer.json()["department_id"] == dept2.json()["id"]


def test_employee_promotion() -> None:
    dept = client.post("/departments", json={"name": "Engineering"})
    employee = client.post(
        "/employees",
        json={"name": "Mia", "department_id": dept.json()["id"], "title": "Engineer"},
    )
    promotion = client.post(
        f"/employees/{employee.json()['id']}/promotion",
        json={
            "new_title": "Senior Engineer",
            "effective_date": "2026-02-01",
            "reason": "performance",
        },
    )
    assert promotion.status_code == 200
    assert promotion.json()["title"] == "Senior Engineer"


def test_promotion_workflow() -> None:
    dept = client.post("/departments", json={"name": "Product"})
    employee = client.post(
        "/employees",
        json={"name": "Sam", "department_id": dept.json()["id"], "title": "PM"},
    )
    request = client.post(
        "/promotions/requests",
        json={
            "employee_id": employee.json()["id"],
            "new_title": "Senior PM",
            "effective_date": "2026-03-01",
            "reason": "performance",
        },
    )
    assert request.status_code == 200
    request_id = request.json()["id"]
    decision = client.post(
        f"/promotions/requests/{request_id}/decision",
        json={"approved": True, "approver": "director_1"},
    )
    assert decision.status_code == 200
    finalize = client.post(
        f"/promotions/requests/{request_id}/finalize",
        json={"hr_reviewer": "hr_lead"},
    )
    assert finalize.status_code == 200


def test_salary_adjustment_flow() -> None:
    dept = client.post("/departments", json={"name": "HR"})
    employee = client.post(
        "/employees",
        json={"name": "Ivy", "department_id": dept.json()["id"], "title": "HR"},
    )
    request = client.post(
        "/salary/adjustments",
        json={
            "employee_id": employee.json()["id"],
            "current_salary": 5000,
            "proposed_salary": 5500,
            "effective_date": "2026-02-01",
            "reason": "performance",
        },
    )
    assert request.status_code == 200
    request_id = request.json()["id"]
    decision = client.post(
        f"/salary/adjustments/{request_id}/decision",
        json={"approved": True, "approver": "hr_lead", "level": "hr"},
    )
    assert decision.status_code == 200
    assert decision.json()["status"] in {"approved", "pending"}


def test_onboarding_flow() -> None:
    dept = client.post("/departments", json={"name": "IT"})
    employee = client.post(
        "/employees",
        json={"name": "Zoe", "department_id": dept.json()["id"], "title": "IT"},
    )
    case = client.post(
        "/onboarding/cases",
        json={
            "employee_id": employee.json()["id"],
            "start_date": "2026-02-03",
            "equipment": "laptop",
            "buddy": "alice",
        },
    )
    assert case.status_code == 200
    case_id = case.json()["id"]
    step = client.post(
        f"/onboarding/cases/{case_id}/steps",
        json={"step": "account_setup", "completed": True, "note": "done"},
    )
    assert step.status_code == 200
    finalize = client.post(
        f"/onboarding/cases/{case_id}/finalize",
        json={"hr_reviewer": "hr_lead"},
    )
    assert finalize.status_code == 200


def test_offboarding_flow() -> None:
    dept = client.post("/departments", json={"name": "Ops"})
    employee = client.post(
        "/employees",
        json={"name": "Leo", "department_id": dept.json()["id"], "title": "Ops"},
    )
    case = client.post(
        "/offboarding/cases",
        json={
            "employee_id": employee.json()["id"],
            "last_workday": "2026-02-28",
            "reason": "resignation",
            "manager": "mgr_a",
        },
    )
    assert case.status_code == 200
    case_id = case.json()["id"]
    step = client.post(
        f"/offboarding/cases/{case_id}/steps",
        json={"step": "asset_return", "completed": True, "note": "returned"},
    )
    assert step.status_code == 200
    finalize = client.post(
        f"/offboarding/cases/{case_id}/finalize",
        json={"hr_reviewer": "hr_lead"},
    )
    assert finalize.status_code == 200


def test_training_flow() -> None:
    dept = client.post("/departments", json={"name": "Enablement"})
    employee = client.post(
        "/employees",
        json={"name": "Nina", "department_id": dept.json()["id"], "title": "AE"},
    )
    training = client.post(
        "/trainings",
        json={"name": "Sales Bootcamp", "capacity": 2, "trainer": "trainer_a"},
    )
    assert training.status_code == 200
    training_id = training.json()["id"]
    enroll = client.post(
        f"/trainings/{training_id}/enroll",
        json={"employee_id": employee.json()["id"], "status": "registered"},
    )
    assert enroll.status_code == 200
    exam = client.post(
        f"/trainings/{training_id}/exam",
        json={"employee_id": employee.json()["id"], "score": 85},
    )
    assert exam.status_code == 200
    complete = client.post(
        f"/trainings/{training_id}/complete",
        json={"employee_id": employee.json()["id"], "score": 92},
    )
    assert complete.status_code == 200


def test_training_complete_requires_exam() -> None:
    dept = client.post("/departments", json={"name": "Learning"})
    employee = client.post(
        "/employees",
        json={"name": "Owen", "department_id": dept.json()["id"], "title": "CS"},
    )
    training = client.post(
        "/trainings",
        json={"name": "Security 101", "capacity": 1, "trainer": "trainer_b"},
    )
    training_id = training.json()["id"]
    client.post(
        f"/trainings/{training_id}/enroll",
        json={"employee_id": employee.json()["id"], "status": "registered"},
    )
    complete = client.post(
        f"/trainings/{training_id}/complete",
        json={"employee_id": employee.json()["id"], "score": 80},
    )
    assert complete.status_code == 400


def test_travel_request_flow() -> None:
    dept = client.post("/departments", json={"name": "Field"})
    employee = client.post(
        "/employees",
        json={"name": "Paul", "department_id": dept.json()["id"], "title": "SE"},
    )
    request = client.post(
        "/travel/requests",
        json={
            "employee_id": employee.json()["id"],
            "destination": "Tokyo",
            "days": 3,
            "reason": "conference",
        },
    )
    assert request.status_code == 200
    request_id = request.json()["id"]
    decision = client.post(
        f"/travel/requests/{request_id}/decision",
        json={"approved": True, "approver": "manager_1"},
    )
    assert decision.status_code == 200
    review = client.post(
        f"/travel/requests/{request_id}/review",
        json={"verified": True, "reviewer": "finance_1"},
    )
    assert review.status_code == 200


def test_attendance_anomaly_flow() -> None:
    dept = client.post("/departments", json={"name": "Ops"})
    employee = client.post(
        "/employees",
        json={"name": "Quinn", "department_id": dept.json()["id"], "title": "Ops"},
    )
    checkin = client.post(
        f"/employees/{employee.json()['id']}/attendance",
        json={"status": "in", "note": "late"},
    )
    assert checkin.status_code == 200
    duplicate = client.post(
        f"/employees/{employee.json()['id']}/attendance",
        json={"status": "in", "note": "duplicate"},
    )
    assert duplicate.status_code == 409
    anomaly = client.post(
        "/attendance/anomalies",
        json={
            "employee_id": employee.json()["id"],
            "anomaly_type": "late",
            "note": "manual_report",
        },
    )
    assert anomaly.status_code == 200
    anomaly_id = anomaly.json()["id"]
    resolve = client.post(
        f"/attendance/anomalies/{anomaly_id}/resolve",
        json={"resolution": "manager_confirmed"},
    )
    assert resolve.status_code == 200
    stats = client.get("/attendance/stats")
    assert stats.status_code == 200


def test_attendance_future_timestamp() -> None:
    dept = client.post("/departments", json={"name": "Field"})
    employee = client.post(
        "/employees",
        json={"name": "Tina", "department_id": dept.json()["id"], "title": "Field"},
    )
    future_ts = (datetime.utcnow() + timedelta(hours=2)).isoformat() + "Z"
    response = client.post(
        f"/employees/{employee.json()['id']}/attendance",
        json={"status": "in", "timestamp": future_ts},
    )
    assert response.status_code == 400


def test_asset_management_flow() -> None:
    dept = client.post("/departments", json={"name": "IT"})
    employee = client.post(
        "/employees",
        json={"name": "Riley", "department_id": dept.json()["id"], "title": "IT"},
    )
    asset = client.post(
        "/assets",
        json={"asset_type": "laptop", "serial_number": "SN-12345", "model": "M2"},
    )
    assert asset.status_code == 200
    asset_id = asset.json()["id"]
    assign = client.post(
        f"/assets/{asset_id}/assign",
        json={"employee_id": employee.json()["id"], "note": "new_hire"},
    )
    assert assign.status_code == 200
    returned = client.post(
        f"/assets/{asset_id}/return",
        json={"condition": "good", "note": "ok"},
    )
    assert returned.status_code == 200
    retired = client.post(
        f"/assets/{asset_id}/retire",
        json={"reason": "obsolete"},
    )
    assert retired.status_code == 200


def test_satisfaction_survey() -> None:
    dept = client.post("/departments", json={"name": "People"})
    employee = client.post(
        "/employees",
        json={"name": "Uma", "department_id": dept.json()["id"], "title": "People Ops"},
    )
    survey = client.post(
        "/surveys/satisfaction",
        json={
            "employee_id": employee.json()["id"],
            "score": 4,
            "comment": "good",
            "category": "culture",
        },
    )
    assert survey.status_code == 200


def test_health_declaration() -> None:
    dept = client.post("/departments", json={"name": "Health"})
    employee = client.post(
        "/employees",
        json={"name": "Vera", "department_id": dept.json()["id"], "title": "Nurse"},
    )
    declaration = client.post(
        "/health/declarations",
        json={
            "employee_id": employee.json()["id"],
            "temperature": 36.8,
            "symptoms": ["cough"],
            "risk_level": "low",
            "note": "ok",
        },
    )
    assert declaration.status_code == 200


def test_department_merge() -> None:
    dept_a = client.post("/departments", json={"name": "Alpha"})
    dept_b = client.post("/departments", json={"name": "Beta"})
    employee = client.post(
        "/employees",
        json={"name": "Will", "department_id": dept_a.json()["id"], "title": "Ops"},
    )
    merge = client.post(
        "/departments/merge",
        json={
            "source_department_id": dept_a.json()["id"],
            "target_department_id": dept_b.json()["id"],
            "reason": "reorg",
        },
    )
    assert merge.status_code == 200
    assert employee.json()["id"] in merge.json()["moved_employees"]
