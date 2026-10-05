"""Explicit network smoke check; output contains no secrets or raw API replies."""
import asyncio
import json
from datetime import date, timedelta
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["VOYAGEPLUS_ENABLE_LLM"] = "false"
os.environ["VOYAGEPLUS_TRANSPORT"] = "local"
from agents.orchestrateur_agent.adk_coordinator import plan_trip


async def main():
    start = date.today() + timedelta(days=7)
    result = await plan_trip({"origin": "Paris", "destination": "Rome", "start_date": start.isoformat(), "end_date": (start + timedelta(days=3)).isoformat(), "budget": 1500})
    flights = result["flights"]
    print(json.dumps({
        "framework": result["architecture"]["framework"],
        "outbound_flights": len(flights.get("aller", [])),
        "return_flights": len(flights.get("retour", [])),
        "stays": len(result["stay"]) if isinstance(result["stay"], list) else 0,
        "activities": len(result["activities"]),
        "weather_available": bool(result["weather"]) and not result["weather"].get("error"),
        "agents_with_errors": list(result["errors"]),
        "ai_status": result["ai"]["status"],
        "estimated_subtotal_eur": result["budget"]["estimated_subtotal_eur"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
