import httpx
import math
import hashlib
import asyncio
from datetime import datetime

OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.openstreetmap.ru/api/interpreter",
]

USER_AGENT = "VoyagePlus-PFE/1.0"

ALLOWED_TYPES = {"hotel", "hostel", "guest_house"}
BASE_PRICE = {"hotel": 85, "hostel": 55, "guest_house": 65}

CITY_FACTOR = {
    "paris": 1.30,
    "london": 1.45,
    "tokyo": 1.35,
    "new york": 1.55,
    "madrid": 1.10,
    "barcelona": 1.10,
    "casablanca": 0.90,
}

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    p = math.pi / 180.0
    dlat = (lat2 - lat1) * p
    dlon = (lon2 - lon1) * p
    a = (math.sin(dlat/2)**2 +
         math.cos(lat1*p) * math.cos(lat2*p) * math.sin(dlon/2)**2)
    return 2 * R * math.asin(math.sqrt(a))

def nights(start, end):
    try:
        d1 = datetime.fromisoformat(start).date()
        d2 = datetime.fromisoformat(end).date()
        return max((d2 - d1).days, 1)
    except Exception:
        return 1

def stable_multiplier(*parts: str) -> float:
    s = "|".join([p for p in parts if p is not None])
    h = hashlib.md5(s.encode("utf-8")).hexdigest()
    v = int(h[:4], 16) / 65535.0
    return 0.85 + v * (1.25 - 0.85)

# ---- geocoding ----

async def geocode_city(client, city: str):
    try:
        r = await client.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": city, "format": "json", "limit": 1},
            headers={"User-Agent": USER_AGENT, "Accept-Language": "en"},
            timeout=20
        )
        if r.status_code != 200:
            return None
        data = r.json()
        if not data:
            return None
        return float(data[0]["lat"]), float(data[0]["lon"]), data[0].get("display_name", city)
    except Exception:
        return None

def overpass_query_around(lat: float, lon: float, radius_m: int, types):
    type_regex = "|".join(types)
    return f"""
    [out:json][timeout:25];
    (
      node["tourism"~"^({type_regex})$"](around:{radius_m},{lat},{lon});
      way["tourism"~"^({type_regex})$"](around:{radius_m},{lat},{lon});
      relation["tourism"~"^({type_regex})$"](around:{radius_m},{lat},{lon});
    );
    out center 60;
    """

async def overpass_fetch(client, query: str):
    for url in OVERPASS_URLS:
        try:
            r = await client.post(url, data=query, headers={"User-Agent": USER_AGENT}, timeout=30)
            if r.status_code == 200:
                js = r.json()
                elements = js.get("elements", [])
                if isinstance(elements, list):
                    return elements
        except Exception:
            continue
    return None

_reverse_cache = {}

def _format_reverse_address(addr: dict) -> str:
    """
    Construit une adresse 'propre' depuis Nominatim reverse.
    """
    house_number = addr.get("house_number")
    road = addr.get("road") or addr.get("pedestrian") or addr.get("footway")
    postcode = addr.get("postcode")
    city = addr.get("city") or addr.get("town") or addr.get("village")
    country = addr.get("country")

    line1 = ""
    if road and house_number:
        line1 = f"{house_number} {road}"
    elif road:
        line1 = str(road)

    line2 = " ".join([x for x in [postcode, city] if x])
    parts = [p for p in [line1, line2, country] if p]

    return ", ".join(parts) if parts else "Adresse non disponible"

async def reverse_geocode_address(client, lat: float, lon: float) -> str:
    """
    Retourne une adresse texte via Nominatim reverse.
    """
    key = f"{lat:.5f},{lon:.5f}"
    if key in _reverse_cache:
        return _reverse_cache[key]

    try:
        r = await client.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"lat": lat, "lon": lon, "format": "jsonv2", "addressdetails": 1},
            headers={"User-Agent": USER_AGENT, "Accept-Language": "en"},
            timeout=20
        )
        if r.status_code != 200:
            _reverse_cache[key] = "Adresse non disponible"
            return _reverse_cache[key]

        js = r.json()
        addr = js.get("address", {})
        formatted = _format_reverse_address(addr)

        _reverse_cache[key] = formatted
        return formatted
    except Exception:
        _reverse_cache[key] = "Adresse non disponible"
        return _reverse_cache[key]

async def execute(request: dict):
    city = (request.get("destination") or "").strip()
    if not city:
        return {"stays": "❌ Destination manquante"}

    start = request.get("start_date")
    end = request.get("end_date")
    n = nights(start, end)

    budget_per_night = request.get("budget_per_night")
    try:
        budget_per_night = float(budget_per_night) if budget_per_night not in (None, "", 0) else None
    except Exception:
        budget_per_night = None

    priority = (request.get("priority") or "best_location").strip().lower()
    if priority not in {"best_location", "cheapest"}:
        priority = "best_location"

    stay_type = (request.get("type") or "").strip().lower()
    types = [stay_type] if stay_type in ALLOWED_TYPES else ["hotel", "hostel", "guest_house"]

    async with httpx.AsyncClient() as client:
        geo = await geocode_city(client, city)
        if not geo:
            return {"stays": f"❌ Ville '{city}' introuvable (géocodage OSM)."}

        center_lat, center_lon, display = geo
        city_key = display.split(",")[0].strip().lower()
        factor_city = CITY_FACTOR.get(city_key, 1.0)

        query = overpass_query_around(center_lat, center_lon, radius_m=10000, types=types)
        elements = await overpass_fetch(client, query)

        if not elements:
            return {"stays": "Aucun hébergement trouvé."}

        raw = []
        for e in elements:
            tags = e.get("tags") or {}
            t = (tags.get("tourism") or "hotel").lower()
            if t not in ALLOWED_TYPES:
                continue

            name = tags.get("name") or "Hébergement"
            lat = e.get("lat") or (e.get("center") or {}).get("lat")
            lon = e.get("lon") or (e.get("center") or {}).get("lon")
            if lat is None or lon is None:
                continue

            lat = float(lat)
            lon = float(lon)
            dist_km = haversine_km(center_lat, center_lon, lat, lon)

            base = BASE_PRICE.get(t, 80)
            factor_loc = 1.18 if dist_km < 2 else (1.08 if dist_km < 5 else 0.98)
            var = stable_multiplier(name, f"{lat:.5f}", f"{lon:.5f}")

            price_night = int(round(base * factor_city * factor_loc * var))
            price_night = max(25, min(price_night, 350))
            total = price_night * n

            if budget_per_night is not None and price_night > budget_per_night:
                continue

            dist_score = max(0.0, 1.0 - (dist_km / 10.0))
            price_score = max(0.0, 1.0 - (price_night / 250.0))
            score = (0.70 * dist_score + 0.30 * price_score) if priority == "best_location" else (0.70 * price_score + 0.30 * dist_score)

            raw.append({
                "name": name,
                "type": t,
                "distance_km": round(dist_km, 2),
                "price_per_night_eur": price_night,
                "total_price_eur": total,
                "score": round(score, 3),
                "lat": round(lat, 6),
                "lon": round(lon, 6),
                "source": "OpenStreetMap",
            })

        if not raw:
            return {"stays": "Aucun résultat dans le budget / filtres actuels."}


        raw.sort(key=lambda x: (-x["score"], x["price_per_night_eur"], x["distance_km"]))
        top = raw[:5]

        for i, item in enumerate(top):
            item["address"] = await reverse_geocode_address(client, item["lat"], item["lon"])
            if i < len(top) - 1:
                await asyncio.sleep(0.9)

        return {"stays": top}
