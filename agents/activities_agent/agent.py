import httpx
import math
from common.geoapify import city_places
from common.osm import geocode_city as lookup_city, overpass_fetch as fetch_places

USER_AGENT = "VoyagePlus-PFE/1.1"

CATEGORIES = {
    "top": [
        ('tourism', 'attraction'),
        ('tourism', 'museum'),
        ('historic', 'monument'),
        ('leisure', 'park'),
        ('tourism', 'viewpoint'),
    ]
}

WEIGHTS = {
    ("tourism", "attraction"): 1.00,
    ("tourism", "museum"): 0.95,
    ("historic", "monument"): 0.95,
    ("leisure", "park"): 0.85,
    ("tourism", "viewpoint"): 0.90,
}


async def geocode_city(client, city):
    result = await lookup_city(client, city)
    return result[:2] if result else None


def overpass_query(lat, lon, radius_m, filters):
    q = []
    for k, v in filters:
        q.append(f'node["{k}"="{v}"](around:{radius_m},{lat},{lon});')
    return f"""
    [out:json][timeout:12];
    (
      {"".join(q)}
    );
    out body 50;
    """

async def overpass_fetch(client, query):
    # Try the same fallback servers as lodging instead of relying on one endpoint.
    result = await fetch_places(client, query)
    return result


def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    p = math.pi / 180
    dlat = (lat2 - lat1) * p
    dlon = (lon2 - lon1) * p
    a = math.sin(dlat/2)**2 + math.cos(lat1*p)*math.cos(lat2*p)*math.sin(dlon/2)**2
    return 2 * R * math.asin(math.sqrt(a))

def extract_name(tags):
    return tags.get("name") or tags.get("name:en") or tags.get("name:it")

def detect_label(tags):
    if tags.get("tourism") == "museum":
        return "Musée"
    if tags.get("historic") == "monument":
        return "Monument"
    if tags.get("leisure") == "park":
        return "Parc"
    return "Attraction"

def interest_weight(tags):
    for k, v in tags.items():
        if (k, v) in WEIGHTS:
            return WEIGHTS[(k, v)]
    return 0.7


async def execute(request):
    city = request.get("destination")
    if not city:
        return {"activities": []}

    async with httpx.AsyncClient() as client:
        provider_result = await city_places(client, city, "tourism.sights,entertainment.museum,leisure.park", 7000)
        if provider_result is not None:
            geo, elements = provider_result
            lat, lon = geo[:2]
        else:
            geo = await geocode_city(client, city)
            if not geo:
                return {"activities": [], "error": "Destination introuvable ou service de localisation indisponible."}
            lat, lon = geo
            query = overpass_query(lat, lon, 7000, CATEGORIES["top"])
            elements = await overpass_fetch(client, query)

        if elements is None:
            return {"activities": [], "error": "Recherche d'activités indisponible : les serveurs OpenStreetMap n'ont pas répondu. Réessayez plus tard."}

        activities = []

        for e in elements:
            tags = e.get("tags", {})
            name = extract_name(tags)
            if not name:
                continue

            dist = haversine(lat, lon, e["lat"], e["lon"])
            score = round(0.6 * interest_weight(tags) + 0.4 * (1 / (1 + dist)), 3)

            activities.append({
                "name": name,
                "category": detect_label(tags),
                "distance_km": round(dist, 2),
                "score": score,
                "source": e.get("source", "OpenStreetMap"),
                "address": e.get("address"),
                "opening_hours": tags.get("opening_hours"),
                "website": tags.get("website"),
                "fee": tags.get("fee"),
                "price_eur": None,
                "availability_verified": False,
                "map_url": f"https://www.google.com/maps/search/?api=1&query={e['lat']},{e['lon']}"
            })

        activities.sort(key=lambda x: (-x["score"], x["distance_km"]))

        return {"activities": activities[:5]}
