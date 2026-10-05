import os
import unittest
from datetime import date, timedelta
from unittest.mock import AsyncMock, patch
import httpx
from agents.stay_agent import agent as stays
from agents.weather_agent import agent as weather


class RealAgentTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        stays._hotel_cache.clear()
        start = date.today() + timedelta(days=2)
        self.trip = {'destination': 'Rome', 'start_date': start.isoformat(),
                     'end_date': (start + timedelta(days=5)).isoformat(), 'budget_per_night': 150}

    async def test_hotel_preserves_provider_total_without_nightly_multiplication(self):
        calls = []
        def handler(request):
            calls.append(request)
            self.assertEqual(request.url.params['adults'], '1')
            self.assertEqual(request.url.params['check_in_date'], self.trip['start_date'])
            return httpx.Response(200, json={'properties': [
                {'name': 'Hotel réel', 'rate_per_night': {'extracted_lowest': 97},
                 'total_rate': {'extracted_lowest': 477}, 'overall_rating': 4.6},
                {'name': 'Prix absent'},
            ]})
        original = httpx.AsyncClient
        with patch.dict(os.environ, {'SERPAPI_API_KEY': 'test'}), patch.object(stays.httpx, 'AsyncClient', side_effect=lambda: original(transport=httpx.MockTransport(handler))):
            result = await stays.execute(self.trip)
            again = await stays.execute(self.trip)
        self.assertEqual(len(calls), 1)
        self.assertEqual(result, again)
        self.assertEqual(len(result['stays']), 1)
        self.assertEqual(result['stays'][0]['total_price_eur'], 477)
        self.assertEqual(result['stays'][0]['price_kind'], 'observed')
        self.assertFalse(result['stays'][0]['availability_verified'])

    async def test_hotel_outage_never_generates_an_estimated_price(self):
        original = httpx.AsyncClient
        with patch.dict(os.environ, {'SERPAPI_API_KEY': 'test'}), patch.object(stays.httpx, 'AsyncClient', side_effect=lambda: original(transport=httpx.MockTransport(lambda request: httpx.Response(429)))):
            result = await stays.execute(self.trip)
        self.assertFalse(result['stays'])
        self.assertIn('Quota', result['error'])

    async def test_forecast_filters_trip_dates_and_reports_missing_dates(self):
        def handler(request):
            if 'geocoding' in request.url.host:
                return httpx.Response(200, json={'results': [{'latitude': 41.9, 'longitude': 12.5}]})
            return httpx.Response(200, json={'timezone': 'Europe/Rome', 'daily': {
                'time': [date.today().isoformat(), self.trip['start_date']],
                'temperature_2m_min': [12, 13], 'temperature_2m_max': [20, 22],
                'precipitation_probability_max': [0, 40], 'weather_code': [0, 3]}})
        original = httpx.AsyncClient
        with patch.object(weather, 'current_weather', AsyncMock(return_value={'weather': {'temperature': '21°C'}})), patch.object(weather.httpx, 'AsyncClient', side_effect=lambda: original(transport=httpx.MockTransport(handler))):
            result = (await weather.execute(self.trip))['weather']
        self.assertEqual(len(result['daily']), 1)
        self.assertEqual(result['daily'][0]['date'], self.trip['start_date'])
        self.assertEqual(result['temperature'], '21°C')
        self.assertIn('16 jours', result['warnings'][0])
