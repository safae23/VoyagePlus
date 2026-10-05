import json
import os
import asyncio
import socket
import threading
import uvicorn
import unittest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from google.adk.models.lite_llm import LiteLlm
from agents.adk_agents import build_specialist
from agents.orchestrateur_agent import adk_coordinator as coordinator
from common.adk_runtime import run_agent
from common.contracts import TripRequest

PAYLOAD = {"origin": "Paris", "destination": "Rome", "start_date": "2027-05-10", "end_date": "2027-05-13", "budget": 1000}



class AdkTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        env = patch.dict(os.environ, {"SERPAPI_API_KEY": "test"})
        env.start()
        self.addCleanup(env.stop)
        mock = patch("agents.flight_agent.agent.offers", AsyncMock(side_effect=lambda client, departure, arrival, day, key: [{"price": 152, "date": day}]))
        mock.start()
        self.addCleanup(mock.stop)

    async def test_real_adk_runner_invokes_flight_tool(self):
        result = json.loads(await run_agent(build_specialist("flight"), PAYLOAD))
        self.assertTrue(result["flights"]["aller"])
        self.assertEqual(result["flights"]["retour"][0]["date"], PAYLOAD["end_date"])

    async def test_remote_a2a_agent_over_http(self):
        from common.api import create_app
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        app = create_app(specialist="flight", port=port)
        server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
        thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
        thread.start()
        try:
            for _ in range(100):
                if server.started:
                    break
                await asyncio.sleep(.05)
            self.assertTrue(server.started)
            with patch.dict(os.environ, {"FLIGHT_AGENT_URL": f"http://127.0.0.1:{port}"}):
                result = await coordinator.search("flight", PAYLOAD, "a2a")
            self.assertTrue(result["flights"]["aller"])
            self.assertTrue(result["flights"]["retour"])
        finally:
            server.should_exit = True
            await asyncio.to_thread(thread.join, 5)
            sock.close()

    async def test_coordinator_budget_and_partial_failure(self):
        observed = {}
        async def search(kind, payload, transport):
            observed[kind] = payload
            if kind == "weather":
                raise RuntimeError("offline")
            return {"flight": {"flights": {"aller": [{"price": 100}], "retour": [{"price": 120}]}},
                    "stay": {"stays": [{"name": "Hotel", "total_price_eur": 300}]},
                    "activities": {"activities": [{"name": "Museum"}]}}[kind]
        with patch.object(coordinator, "search", side_effect=search), patch.dict(os.environ, {"VOYAGEPLUS_ENABLE_LLM": "false", "VOYAGEPLUS_TRANSPORT": "local"}):
            result = await coordinator.plan_trip(PAYLOAD)
        self.assertEqual(result["budget"]["estimated_subtotal_eur"], 520)
        self.assertEqual(result["budget"]["remaining_eur"], 480)
        self.assertEqual(observed["stay"]["budget_per_night"], 166.67)
        self.assertIn("weather", result["errors"])
        self.assertEqual(result["activities"], [{"name": "Museum"}])
        self.assertEqual(result["ai"]["status"], "disabled")
        self.assertFalse(result["budget"]["complete_total"])

    async def test_litellm_agent_uses_adk_model_lifecycle(self):
        trip = TripRequest.model_validate(PAYLOAD)
        with patch.object(coordinator, "LiteLlm", return_value=LiteLlm(model="openai/test", mock_response="Synthèse de test fondée sur les résultats.")), patch.dict(os.environ, {"VOYAGEPLUS_ENABLE_LLM": "true", "GEMINI_API_KEY": "test-key", "VOYAGEPLUS_MODEL": "gemini/test"}):
            summary, status = await coordinator.synthesize(trip, {"flights": {}}, {"estimated_subtotal_eur": None})
        self.assertIn("Synthèse de test", summary)
        self.assertEqual(status["status"], "ok")

    async def test_model_failure_preserves_fallback(self):
        trip = TripRequest.model_validate(PAYLOAD)
        with patch.object(coordinator, "run_agent", AsyncMock(side_effect=RuntimeError("offline"))), patch.dict(os.environ, {"VOYAGEPLUS_ENABLE_LLM": "true", "GEMINI_API_KEY": "test-key", "VOYAGEPLUS_MODEL": "gemini/test"}):
            summary, status = await coordinator.synthesize(trip, {}, {"estimated_subtotal_eur": None})
        self.assertIn("Google Flights", summary)
        self.assertEqual(status["status"], "error")


class EndpointTests(unittest.TestCase):
    def setUp(self):
        env = patch.dict(os.environ, {"SERPAPI_API_KEY": "test"})
        env.start()
        self.addCleanup(env.stop)
        mock = patch("agents.flight_agent.agent.offers", AsyncMock(side_effect=lambda client, departure, arrival, day, key: [{"price": 152, "date": day}]))
        mock.start()
        self.addCleanup(mock.stop)

    def test_invalid_trip_is_rejected_before_execution(self):
        from agents.orchestrateur_agent.__main__ import app
        with TestClient(app) as client:
            for update in ({"end_date": PAYLOAD["start_date"]}, {"budget": -1}, {"destination": " "}, {"start_date": "invalid"}):
                self.assertEqual(client.post("/run", json={**PAYLOAD, **update}).status_code, 422)

    def test_complete_trip_endpoint_response_contract(self):
        from agents.orchestrateur_agent.__main__ import app
        async def search(kind, payload, transport):
            return {"flight": {"flights": {"aller": [{"price": 100}], "retour": [{"price": 100}]}},
                    "stay": {"stays": [{"total_price_eur": 300}]},
                    "activities": {"activities": []}, "weather": {"weather": {"error": "offline"}}}[kind]
        with patch.object(coordinator, "search", side_effect=search), patch.dict(os.environ, {"VOYAGEPLUS_ENABLE_LLM": "false", "VOYAGEPLUS_TRANSPORT": "local"}), TestClient(app) as client:
            response = client.post("/run", json=PAYLOAD)
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["budget"]["estimated_subtotal_eur"], 500)
        self.assertEqual(result["architecture"]["framework"], "google-adk")
        self.assertEqual(result["ai"]["status"], "disabled")
        self.assertIn("weather", result["errors"])

    def test_a2a_card_and_message_execute_real_adk_tool(self):
        from agents.flight_agent.__main__ import app
        with TestClient(app) as client:
            card = client.get("/a2a/.well-known/agent-card.json")
            self.assertEqual(card.status_code, 200)
            self.assertEqual(card.json()["url"], "http://127.0.0.1:8001/a2a/")
            response = client.post("/a2a/", json={"jsonrpc": "2.0", "id": "test", "method": "message/send", "params": {"message": {"role": "user", "messageId": "test-trip", "parts": [{"kind": "text", "text": json.dumps(PAYLOAD)}]}}})
            self.assertEqual(response.status_code, 200)
            body = response.json()
            self.assertNotIn("error", body)
            self.assertIn("aller", json.dumps(body))
            self.assertIn("retour", json.dumps(body))
