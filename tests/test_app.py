import os

os.environ["SIM_ENABLED"] = "false"
os.environ["OTEL_SDK_DISABLED"] = "true"

from fastapi.testclient import TestClient

from app.main import create_app


client = TestClient(create_app())


def test_health() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["service"] == "logpulse"


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
