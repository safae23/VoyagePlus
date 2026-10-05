import os
from datetime import datetime, timezone

import httpx
from dotenv import load_dotenv

load_dotenv()
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

async def current_weather(request: dict):
    city = request.get("destination") or request.get("city")

    if not city:
        return {"weather": {"error": "Destination manquante"}}

    if not OPENWEATHER_API_KEY:
        return {"weather": {"error": "Clé API OpenWeather manquante"}}

    url = (
        "https://api.openweathermap.org/data/2.5/weather"
        f"?q={city}&appid={OPENWEATHER_API_KEY}&units=metric&lang=fr"
    )

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10)

        if response.status_code != 200:
            return {
                "weather": {
                    "error": f"Erreur OpenWeather ({response.status_code})"
                }
            }

        data = response.json()

        temperature = round(data["main"]["temp"])
        humidity = data["main"]["humidity"]
        condition = data["weather"][0]["description"]

        if temperature < 10:
            tip = "🧥 Prévoyez des vêtements chauds."
        elif temperature > 30:
            tip = "🥵 Hydratez-vous et évitez les sorties."
        else:
            tip = "😊 Conditions agréables pour visiter."


        return {
            "weather": {
                "city": city,
                "source": "OpenWeather",
                "period": "current",
                "temperature": f"{temperature}°C",
                "humidity": f"{humidity}%",
                "condition": condition,
                "tip": tip
            }
        }

    except Exception:
        return {
            "weather": {
                "error": "Service météo temporairement indisponible."
            }
        }


async def execute(request: dict):
    current = (await current_weather(request)).get("weather", {})
    current_error = current.pop("error", None)
    city = request.get("destination") or request.get("city")
    output = {**current, "source": "OpenWeather / Open-Meteo", "period": "current_and_forecast", "daily": [],
              "observed_at": datetime.now(timezone.utc).isoformat()}
    warnings = [current_error] if current_error else []
    try:
        start, end = request["start_date"], request["end_date"]
        async with httpx.AsyncClient() as client:
            geo = await client.get("https://geocoding-api.open-meteo.com/v1/search", params={"name": city, "count": 1, "language": "fr"}, timeout=8)
            geo.raise_for_status()
            places = geo.json().get("results", [])
            if not places: raise ValueError()
            place = places[0]
            response = await client.get("https://api.open-meteo.com/v1/forecast", params={
                "latitude": place["latitude"], "longitude": place["longitude"], "timezone": "auto", "forecast_days": 16,
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,weather_code"}, timeout=12)
            response.raise_for_status()
            daily = response.json().get("daily", {})
            for i, day in enumerate(daily.get("time", [])):
                if start <= day <= end:
                    output["daily"].append({"date": day, "min_c": daily["temperature_2m_min"][i],
                        "max_c": daily["temperature_2m_max"][i], "rain_probability_pct": daily["precipitation_probability_max"][i],
                        "weather_code": daily["weather_code"][i]})
            days = {day["date"] for day in output["daily"]}
            if start not in days or end not in days:
                warnings.append("Prévisions limitées aux prochains 16 jours : certaines dates du séjour ne sont pas encore disponibles.")
            output["forecast_timezone"] = response.json().get("timezone")
    except Exception:
        warnings.append("Prévisions du séjour indisponibles. Aucune météo n'est inventée.")
    if warnings: output["warnings"] = warnings
    if not current and not output["daily"]:
        output["error"] = "Météo actuelle et prévisions indisponibles."
    return {"weather": output}
