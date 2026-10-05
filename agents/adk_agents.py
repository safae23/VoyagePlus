"""Four ADK custom agents: deterministic tools preserve source data."""
import json
from typing import Any
from google.adk.agents import BaseAgent
from google.adk.events import Event
from google.adk.tools import FunctionTool, ToolContext
from google.genai import types
from agents.flight_agent.agent import execute as flights
from agents.stay_agent.agent import execute as stays
from agents.activities_agent.agent import execute as activities
from agents.weather_agent.agent import execute as weather


class SearchAgent(BaseAgent):
    search_tool: Any

    async def _run_async_impl(self, ctx):
        text = "".join(p.text or "" for p in ctx.user_content.parts or [])
        payload = json.loads(text)
        result = await self.search_tool.run_async(args={"request": payload}, tool_context=ToolContext(ctx))
        yield Event(author=self.name, content=types.Content(
            role="model", parts=[types.Part(text=json.dumps(result, ensure_ascii=False))]))


def build_specialist(kind):
    handlers = {"flight": flights, "stay": stays, "activities": activities, "weather": weather}
    descriptions = {
        "flight": "Recherche de vols réels Google Flights via SerpApi ; prix observés à confirmer chez le vendeur.",
        "stay": "Offres Google Hotels via SerpApi aux dates demandées, prix observés à confirmer chez le vendeur.",
        "activities": "Recherche et classement des points d'intérêt Geoapify ou OpenStreetMap.",
        "weather": "Météo actuelle OpenWeather et prévisions datées Open-Meteo dans leur horizon disponible.",
    }
    return SearchAgent(name=f"{kind}_agent", description=descriptions[kind],
                       search_tool=FunctionTool(handlers[kind]))
