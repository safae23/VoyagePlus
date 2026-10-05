import unittest
from unittest.mock import AsyncMock, patch
from agents.activities_agent import agent as activities


class PlaceErrorTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        for module in (activities,):
            mock = patch.object(module, "city_places", AsyncMock(return_value=None))
            mock.start()
            self.addCleanup(mock.stop)

    async def test_activity_outage_has_explicit_error(self):
        with patch.object(activities, "geocode_city", AsyncMock(return_value=(41.9, 12.5))), patch.object(activities, "overpass_fetch", AsyncMock(return_value=None)):
            result = await activities.execute({"destination": "Rome"})
        self.assertEqual(result["activities"], [])
        self.assertIn("OpenStreetMap", result["error"])
