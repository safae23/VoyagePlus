import importlib
import unittest
from fastapi.testclient import TestClient


class ServiceTests(unittest.TestCase):
    def test_services_expose_health_and_specialists_only_use_a2a(self):
        for name in ("flight", "stay", "activities", "weather", "orchestrateur"):
            with self.subTest(agent=name):
                module = importlib.import_module(f"agents.{name}_agent.__main__")
                with TestClient(module.app) as client:
                    self.assertEqual(client.get("/health").status_code, 200)
                    self.assertEqual(client.get("/docs").status_code, 200)
                    self.assertEqual(client.get("/", follow_redirects=False).headers["location"], "/docs")
                    if name != "orchestrateur":
                        self.assertEqual(client.post("/run", json={}).status_code, 404)
                        self.assertEqual(client.get("/a2a/.well-known/agent-card.json").status_code, 200)
