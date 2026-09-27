from datetime import datetime, timedelta
import random

# ============================
# ROUTES (UN SEUL SENS)
# ============================

ROUTES = {
    ("Paris", "Rome"): {
        "airlines": ["Air France", "ITA Airways", "Vueling"],
        "duration_min": 125,
        "price_range": (140, 260)
    },
    ("Paris", "Rabat"): {
        "airlines": ["Royal Air Maroc", "Air France", "Transavia"],
        "duration_min": 185,
        "price_range": (180, 350)
    },
    ("Paris", "Madrid"): {
        "airlines": ["Iberia", "Air France", "Ryanair"],
        "duration_min": 130,
        "price_range": (120, 240)
    }
}

TIME_SLOTS = [
    ("06:05", "08:15"),
    ("09:30", "11:40"),
    ("12:45", "14:55"),
    ("15:20", "17:30"),
    ("18:40", "20:50"),
    ("21:25", "23:40")
]

# ============================
# UTILITAIRES
# ============================

def duration_str(minutes):
    return f"{minutes // 60}h {minutes % 60}min"


def get_route(city_from, city_to):
    """
    Trouve la route dans un sens OU l'autre
    """
    if (city_from, city_to) in ROUTES:
        return ROUTES[(city_from, city_to)]
    if (city_to, city_from) in ROUTES:
        return ROUTES[(city_to, city_from)]
    return None


def generate_flights(city_from, city_to, date_str):
    route = get_route(city_from, city_to)
    if not route:
        return []

    flights = []
    used = set()

    for airline in route["airlines"]:
        for _ in range(2):
            dep, arr = random.choice(TIME_SLOTS)

            if (airline, dep) in used:
                continue

            duration = route["duration_min"] + random.randint(-10, 15)
            price = random.randint(*route["price_range"])

            flights.append({
                "airline": airline,
                "departure_time": dep,
                "arrival_time": arr,
                "duration": duration_str(duration),
                "price": round(price, 2),
                "date": date_str
            })

            used.add((airline, dep))

            if len(flights) >= 4:
                return flights

    return flights


# ============================
# POINT D’ENTRÉE STREAMLIT
# ============================

async def execute(request: dict):
    origin = request.get("origin", "Paris").title()
    destination = request.get("destination", "Rome").title()
    start_date = request.get("start_date")
    end_date = request.get("end_date")

    sd = datetime.strptime(start_date, "%Y-%m-%d")
    ed = datetime.strptime(end_date, "%Y-%m-%d")

    if ed <= sd:
        ed = sd + timedelta(days=3)

    flights_aller = generate_flights(origin, destination, sd.strftime("%Y-%m-%d"))
    flights_retour = generate_flights(destination, origin, ed.strftime("%Y-%m-%d"))

    return {
        "flights": {
            "aller": flights_aller,
            "retour": flights_retour
        }
    }
