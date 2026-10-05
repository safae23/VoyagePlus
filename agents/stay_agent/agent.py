import httpx
import math
from datetime import datetime, timezone
import os
import time
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

_hotel_cache = {}

async def execute(request: dict):
    key = os.getenv("SERPAPI_API_KEY", "").strip()
    if not key:
        return {"stays": [], "error": "Clé SerpApi absente pour rechercher les tarifs réels des hôtels."}
    city = str(request.get("destination", "")).strip()
    start, end = request.get("start_date"), request.get("end_date")
    try:
        first, last = datetime.fromisoformat(start).date(), datetime.fromisoformat(end).date()
        if not city or last <= first or first < datetime.now(timezone.utc).date():
            raise ValueError()
    except (ValueError, TypeError):
        return {"stays": [], "error": "Destination ou dates d'hébergement invalides."}
    cache_key = (city.casefold(), start, end, key)
    cached = _hotel_cache.get(cache_key)
    if cached and time.monotonic() - cached[0] < 600:
        items = cached[1]
    else:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("https://serpapi.com/search.json", params={
                    "engine": "google_hotels", "q": f"Hotels in {city}",
                    "check_in_date": start, "check_out_date": end, "adults": 1,
                    "currency": "EUR", "hl": "fr", "api_key": key}, timeout=40)
            if response.status_code in (401, 403):
                return {"stays": [], "error": "Clé SerpApi refusée pour les hôtels."}
            if response.status_code == 429:
                return {"stays": [], "error": "Quota SerpApi atteint pour les hôtels."}
            response.raise_for_status()
            body = response.json()
            if body.get("error"):
                return {"stays": [], "error": "Recherche Google Hotels indisponible pour ces dates."}
            items = []
            observed = datetime.now(timezone.utc).isoformat()
            for prop in body.get("properties", []):
                night = prop.get("rate_per_night", {}).get("extracted_lowest")
                total = prop.get("total_rate", {}).get("extracted_lowest")
                # Keep only provider totals: rounding and taxes may prevent night*nights equality.
                if not all(isinstance(v, (int, float)) and math.isfinite(v) and v >= 0 for v in (night, total)):
                    continue
                link = prop.get("link", "")
                if urlparse(link).scheme != "https": link = ""
                items.append({"name": prop.get("name", "Hébergement"), "type": prop.get("type", "hotel"),
                    "address": prop.get("address") or "Adresse non fournie par Google Hotels",
                    "price_per_night_eur": night, "total_price_eur": total,
                    "score": prop.get("location_rating") or prop.get("overall_rating"),
                    "rating": prop.get("overall_rating"), "location_rating": prop.get("location_rating"),
                    "source": "Google Hotels via SerpApi", "price_kind": "observed", "currency": "EUR",
                    "availability_verified": False, "offer_observed": True,
                    "check_in_date": start, "check_out_date": end, "observed_at": observed,
                    "booking_url": link, "amenities": prop.get("amenities", []),
                    "lat": prop.get("gps_coordinates", {}).get("latitude"),
                    "lon": prop.get("gps_coordinates", {}).get("longitude")})
            if len(_hotel_cache) >= 128: _hotel_cache.pop(next(iter(_hotel_cache)))
            _hotel_cache[cache_key] = (time.monotonic(), items)
        except Exception:
            return {"stays": [], "error": "Service de tarifs hôteliers indisponible. Aucun tarif estimé n'est utilisé."}
    limit = request.get("budget_per_night")
    if limit is not None:
        items = [item for item in items if item["price_per_night_eur"] <= float(limit)]
    if request.get("priority") == "cheapest":
        items = sorted(items, key=lambda item: item["total_price_eur"])
    else:
        items = sorted(items, key=lambda item: (-(item["score"] or 0), item["total_price_eur"]))
    if not items:
        return {"stays": [], "error": "Aucune offre hôtelière avec tarif réel dans les dates et le budget demandés."}
    return {"stays": items[:5]}
