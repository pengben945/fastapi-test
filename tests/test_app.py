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
