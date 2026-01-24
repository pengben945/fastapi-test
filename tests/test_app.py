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
