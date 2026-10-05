"""OpenStreetMap fallback tools used by the activity agent."""
OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.openstreetmap.ru/api/interpreter",
]

USER_AGENT = "VoyagePlus-PFE/1.0"

async def geocode_city(client, city: str):
    try:
        r = await client.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": city, "format": "json", "limit": 1},
            headers={"User-Agent": USER_AGENT, "Accept-Language": "en"},
            timeout=10
        )
        if r.status_code != 200:
            return None
        data = r.json()
        if not data:
            return None
        return float(data[0]["lat"]), float(data[0]["lon"]), data[0].get("display_name", city)
    except Exception:
        return None

async def overpass_fetch(client, query: str):
    for url in OVERPASS_URLS:
        try:
            r = await client.post(url, data=query, headers={"User-Agent": USER_AGENT}, timeout=15)
            if r.status_code == 200:
                js = r.json()
                elements = js.get("elements", [])
                if isinstance(elements, list):
                    return elements
        except Exception:
            continue
    return None

