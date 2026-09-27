import importlib
import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from agents.orchestrateur_agent import task_manager


class ServiceTests(unittest.TestCase):
    def test_all_entrypoints_forward_requests_and_expose_docs(self):
        for name in ("flight", "stay", "activities", "weather", "orchestrateur"):
            with self.subTest(agent=name):
                module = importlib.import_module(f"agents.{name}_agent.__main__")
                handler = AsyncMock(return_value={"ok": True})
                with patch.object(module, "run", handler):
                    client = TestClient(module.create_app(module.run))
                    response = client.post("/run", json={"destination": "Rome"})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), {"ok": True})
                handler.assert_awaited_once_with({"destination": "Rome"})
                self.assertEqual(client.get("/", follow_redirects=False).headers["location"], "/docs")
                self.assertEqual(TestClient(module.app).get("/docs").status_code, 200)

    def test_flight_endpoint_returns_round_trip(self):
        module = importlib.import_module("agents.flight_agent.__main__")
        response = TestClient(module.app).post("/run", json={
            "origin": "Paris", "destination": "Rome",
            "start_date": "2027-05-10", "end_date": "2027-05-13",
        })
        self.assertEqual(response.status_code, 200)
        for direction, expected_date in (("aller", "2027-05-10"), ("retour", "2027-05-13")):
            flights = response.json()["flights"][direction]
            self.assertTrue(flights)
            self.assertTrue(all(f["date"] == expected_date for f in flights))


class OrchestratorTests(unittest.IsolatedAsyncioTestCase):
    async def test_aggregates_all_agents(self):
        results = [
            {"flights": {"aller": [], "retour": []}},
            {"stays": [{"name": "Hotel"}]},
            {"activities": [{"name": "Museum"}]},
            {"weather": {"temperature": "20 C"}},
        ]
        with patch.object(task_manager, "call_agent", AsyncMock(side_effect=results)) as call:
            response = await task_manager.run({"destination": "Rome", "budget": 1000})
        self.assertEqual(call.await_count, 4)
        self.assertEqual(response, {
            "flights": results[0]["flights"], "stay": results[1]["stays"],
            "activities": results[2]["activities"], "weather": results[3]["weather"],
        })

    async def test_one_failed_agent_preserves_other_results(self):
        results = [RuntimeError("unavailable"), {"stays": []},
                   {"activities": [{"name": "Museum"}]}, {"weather": {}}]
        with patch.object(task_manager, "call_agent", AsyncMock(side_effect=results)):
            response = await task_manager.run({"destination": "Rome"})
        self.assertEqual(response["flights"], [])
        self.assertEqual(response["activities"], [{"name": "Museum"}])
