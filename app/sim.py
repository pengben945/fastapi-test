import asyncio
import logging
import os
import random
from typing import Any

import httpx


logger = logging.getLogger("logpulse.sim")


class Simulator:
    def __init__(self, base_url: str, min_wait: float, max_wait: float) -> None:
        self.base_url = base_url.rstrip("/")
        self.min_wait = min_wait
        self.max_wait = max_wait
        self._task: asyncio.Task[None] | None = None
        self._departments: list[int] = []
        self._employees: list[int] = []

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            logger.info("simulator stopped")
        self._task = None

    async def _run(self) -> None:
        actions = [
            "create_department",
            "create_employee",
            "attendance",
            "payroll",
            "leave_request",
            "leave_decision",
            "review_create",
            "review_decision",
            "department_transfer",
            "promotion",
        ]
        async with httpx.AsyncClient(timeout=5.0) as client:
            while True:
                action = random.choice(actions)
                try:
                    await self._perform_action(client, action)
                except Exception as exc:
                    logger.warning("sim action failed: %s", exc)
                await asyncio.sleep(random.uniform(self.min_wait, self.max_wait))

    async def _perform_action(self, client: httpx.AsyncClient, action: str) -> None:
        if action == "create_department":
            payload = {"name": random.choice(["HR", "Finance", "Engineering", "Sales"])}
            response = await client.post(f"{self.base_url}/departments", json=payload)
            if response.status_code == 200:
                department_id = response.json().get("id")
                if isinstance(department_id, int):
                    self._departments.append(department_id)
            return

        if action == "create_employee":
            if not self._departments:
                return
            payload = {
                "name": random.choice(["Alice", "Bob", "Cindy", "David"]),
                "department_id": random.choice(self._departments),
                "title": random.choice(["Analyst", "Engineer", "Manager"]),
            }
            response = await client.post(f"{self.base_url}/employees", json=payload)
            if response.status_code == 200:
                employee_id = response.json().get("id")
                if isinstance(employee_id, int):
                    self._employees.append(employee_id)
            return

        if action == "attendance":
            if not self._employees:
                return
            payload: dict[str, Any] = {
                "status": random.choice(["in", "out"]),
            }
            employee_id = random.choice(self._employees)
            await client.post(
                f"{self.base_url}/employees/{employee_id}/attendance", json=payload
            )
            return

        if action == "leave_request":
            if not self._employees:
                return
            payload = {
                "employee_id": random.choice(self._employees),
                "leave_type": random.choice(["annual", "sick", "personal"]),
                "days": random.randint(1, 5),
                "reason": random.choice(["family", "travel", "medical", "rest"]),
            }
            response = await client.post(f"{self.base_url}/leave/requests", json=payload)
            if response.status_code == 200:
                leave_id = response.json().get("id")
                if isinstance(leave_id, int):
                    setattr(self, "_last_leave_id", leave_id)
            return

        if action == "leave_decision":
            leave_id = getattr(self, "_last_leave_id", None)
            if not leave_id:
                return
            payload = {
                "approved": random.choice([True, False]),
                "approver": random.choice(["hr_lead", "manager_1"]),
            }
            await client.post(
                f"{self.base_url}/leave/requests/{leave_id}/decision", json=payload
            )
            return

        if action == "review_create":
            if not self._employees:
                return
            payload = {
                "employee_id": random.choice(self._employees),
                "period": random.choice(["2025-12", "2026-01"]),
                "score": random.randint(1, 5),
                "summary": random.choice(["solid", "excellent", "needs improvement"]),
            }
            response = await client.post(
                f"{self.base_url}/performance/reviews", json=payload
            )
            if response.status_code == 200:
                review_id = response.json().get("id")
                if isinstance(review_id, int):
                    setattr(self, "_last_review_id", review_id)
            return

        if action == "review_decision":
            review_id = getattr(self, "_last_review_id", None)
            if not review_id:
                return
            payload = {
                "final_rating": random.choice(["A", "B", "C"]),
                "reviewer": random.choice(["hr_lead", "manager_1"]),
            }
            await client.post(
                f"{self.base_url}/performance/reviews/{review_id}/decision", json=payload
            )
            return

        if action == "department_transfer":
            if not self._employees or not self._departments:
                return
            employee_id = random.choice(self._employees)
            payload = {
                "department_id": random.choice(self._departments),
                "reason": random.choice(["reorg", "project shift", "promotion"]),
            }
            await client.post(
                f"{self.base_url}/employees/{employee_id}/transfer", json=payload
            )
            return

        if action == "promotion":
            if not self._employees:
                return
            employee_id = random.choice(self._employees)
            payload = {
                "new_title": random.choice(["Senior Engineer", "Lead", "Manager"]),
                "effective_date": random.choice(["2026-02-01", "2026-03-01"]),
                "reason": random.choice(["performance", "leadership", "tenure"]),
            }
            await client.post(
                f"{self.base_url}/employees/{employee_id}/promotion", json=payload
            )
            return

        payload = {"month": random.choice(["2025-12", "2026-01"])}
        await client.post(f"{self.base_url}/payroll/run", json=payload)


def create_simulator() -> Simulator:
    base_url = os.getenv("SIM_BASE_URL", "http://127.0.0.1:8000")
    min_wait = float(os.getenv("SIM_MIN_WAIT", "0.5"))
    max_wait = float(os.getenv("SIM_MAX_WAIT", "2.0"))
    return Simulator(base_url=base_url, min_wait=min_wait, max_wait=max_wait)
