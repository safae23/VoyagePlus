from common.a2a_client import call_agent
import asyncio

FLIGHT_URL = "http://localhost:8001/run"
STAY_URL = "http://localhost:8002/run"
ACTIVITIES_URL = "http://localhost:8003/run"
WEATHER_URL = "http://localhost:8004/run"


async def run(payload):
    flight_payload = {
        "origin": payload.get("origin"),
        "destination": payload.get("destination"),
        "start_date": payload.get("start_date"),
        "end_date": payload.get("end_date"),
        "budget": payload.get("budget")
    }

    stay_payload = {
        "destination": payload.get("destination"),
        "start_date": payload.get("start_date"),
        "end_date": payload.get("end_date"),
        "budget_per_night": payload.get("budget", 120),
        "priority": payload.get("priority", "best_location")
    }

    activities_payload = {
        "destination": payload.get("destination"),
        "category": payload.get("category", "top"),
        "radius_km": payload.get("radius_km", 10)
    }

    weather_payload = {
        "destination": payload.get("destination")
    }

    flights_task = call_agent(FLIGHT_URL, flight_payload)
    stay_task = call_agent(STAY_URL, stay_payload)
    activities_task = call_agent(ACTIVITIES_URL, activities_payload)
    weather_task = call_agent(WEATHER_URL, weather_payload)

    flights, stay, activities, weather = await asyncio.gather(
        flights_task,
        stay_task,
        activities_task,
        weather_task,
        return_exceptions=True
    )


    flights = flights if isinstance(flights, dict) else {}
    stay = stay if isinstance(stay, dict) else {}
    activities = activities if isinstance(activities, dict) else {}
    weather = weather if isinstance(weather, dict) else {}

    return {
        "flights": flights.get("flights", []),
        "stay": stay.get("stays", []),
        "activities": activities.get("activities", []),
        "weather": weather.get("weather", {})
    }
