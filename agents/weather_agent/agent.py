import os

import httpx
from dotenv import load_dotenv

load_dotenv()
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

async def execute(request: dict):
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
