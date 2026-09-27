import httpx
import math

USER_AGENT = "VoyagePlus-PFE/1.1"

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

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
    r = await client.get(
        "https://nominatim.openstreetmap.org/search",
        params={"q": city, "format": "json", "limit": 1},
        headers={"User-Agent": USER_AGENT},
        timeout=15
    )
    data = r.json()
    if not data:
        return None
    return float(data[0]["lat"]), float(data[0]["lon"])


def overpass_query(lat, lon, radius_m, filters):
    q = []
    for k, v in filters:
        q.append(f'node["{k}"="{v}"](around:{radius_m},{lat},{lon});')
    return f"""
    [out:json][timeout:20];
    (
      {"".join(q)}
    );
    out body 50;
    """

async def overpass_fetch(client, query):
    r = await client.post(
        OVERPASS_URL,
        data=query,
        headers={"User-Agent": USER_AGENT},
        timeout=25
    )
    js = r.json()
    return js.get("elements", [])


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
        geo = await geocode_city(client, city)
        if not geo:
            return {"activities": []}

        lat, lon = geo
        query = overpass_query(lat, lon, 7000, CATEGORIES["top"])
        elements = await overpass_fetch(client, query)

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
                "source": "OpenStreetMap"
            })

        activities.sort(key=lambda x: (-x["score"], x["distance_km"]))

        return {"activities": activities[:5]}
