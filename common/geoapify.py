"""Geoapify adapter returning the same normalized places as the OSM tools."""
import os
import time
import httpx
from dotenv import load_dotenv

load_dotenv()
_cache = {}


async def city_places(client, city, categories, radius):
    key = os.getenv("GEOAPIFY_API_KEY", "").strip()
    if not key:
        return None
    cache_key = (city.strip().casefold(), categories, radius, key)
    cached = _cache.get(cache_key)
    if cached and time.monotonic() - cached[0] < 300:
        return cached[1]
    try:
        response = await client.get("https://api.geoapify.com/v1/geocode/search",
            params={"text": city, "type": "city", "limit": 1, "apiKey": key}, timeout=8)
        response.raise_for_status()
        cities = response.json().get("features", [])
        if not cities:
            return None
        properties = cities[0]["properties"]
        lat, lon = float(properties["lat"]), float(properties["lon"])
        response = await client.get("https://api.geoapify.com/v2/places", params={
            "categories": categories, "filter": f"circle:{lon},{lat},{radius}",
            "bias": f"proximity:{lon},{lat}", "limit": 20, "apiKey": key}, timeout=8)
        response.raise_for_status()
        elements = []
        for feature in response.json().get("features", []):
            prop = feature.get("properties", {})
            coords = feature.get("geometry", {}).get("coordinates", [])
            place_lat = prop.get("lat", coords[1] if len(coords) >= 2 else None)
            place_lon = prop.get("lon", coords[0] if len(coords) >= 2 else None)
            if place_lat is None or place_lon is None:
                continue
            tags = {"name": prop.get("name", ""), "tourism": "attraction"}
            raw_tags = (prop.get("datasource") or {}).get("raw") or {}
            for field in ("opening_hours", "website", "fee", "phone"):
                value = prop.get(field) or raw_tags.get(field)
                if value: tags[field] = value
            cats = prop.get("categories", [])
            for category, tag in [("accommodation.hotel", "hotel"), ("accommodation.hostel", "hostel"),
                                  ("accommodation.guest_house", "guest_house"), ("entertainment.museum", "museum")]:
                if category in cats:
                    tags["tourism"] = tag
                    break
            if "leisure.park" in cats:
                tags["leisure"] = "park"
            elements.append({"lat": float(place_lat), "lon": float(place_lon), "tags": tags,
                             "address": prop.get("formatted"), "source": "Geoapify"})
        result = ((lat, lon, properties.get("city") or city), elements)
        if len(_cache) >= 256:
            _cache.clear()
        _cache[cache_key] = (time.monotonic(), result)
        return result
    except (httpx.HTTPError, ValueError, KeyError, TypeError, IndexError):
        # Never log exception URLs: they contain the API key.
        return None
