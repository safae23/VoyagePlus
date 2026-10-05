import os
import unittest
from unittest.mock import AsyncMock, patch
import httpx
from common import geoapify
from agents.activities_agent import agent as activities


class GeoapifyTests(unittest.IsolatedAsyncioTestCase):
    async def test_normalization_cache_preserves_real_places(self):
        geoapify._cache.clear()
        calls = []
        def handle(request):
            calls.append(request.url.path)
            if request.url.path.endswith("search"):
                data = {"features": [{"properties": {"lat": 41.9, "lon": 12.5, "city": "Rome"}}]}
            else:
                data = {"features": [{"properties": {"lat": 41.91, "lon": 12.51, "name": "Hotel Test", "formatted": "Rome", "categories": ["accommodation.hotel"]}}]}
            return httpx.Response(200, json=data)
        with patch.dict(os.environ, {"GEOAPIFY_API_KEY": "test"}):
            async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
                first = await geoapify.city_places(client, "Rome", "accommodation.hotel", 10000)
                second = await geoapify.city_places(client, "Rome", "accommodation.hotel", 10000)
        self.assertEqual(first, second)
        self.assertEqual(len(calls), 2)
        self.assertEqual(first[1][0]["source"], "Geoapify")
        self.assertEqual(first[1][0]["address"], "Rome")

    async def test_auth_failure_allows_osm_fallback(self):
        geoapify._cache.clear()
        with patch.dict(os.environ, {"GEOAPIFY_API_KEY": "invalid-test"}):
            async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(401))) as client:
                self.assertIsNone(await geoapify.city_places(client, "Rome", "accommodation.hotel", 10000))
        with patch.object(activities, "city_places", AsyncMock(return_value=None)), patch.object(activities, "geocode_city", AsyncMock(return_value=(41.9, 12.5))), patch.object(activities, "overpass_fetch", AsyncMock(return_value=[])) as fallback:
            result = await activities.execute({"destination": "Rome"})
        fallback.assert_awaited_once()
        self.assertEqual(result["activities"], [])
