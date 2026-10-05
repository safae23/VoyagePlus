import os
import unittest
from datetime import date, timedelta
from unittest.mock import patch
import httpx
from agents.flight_agent import agent
from common.contracts import TripRequest
from common.planning import budget_summary


class FlightTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        agent._cache.clear()
        start = date.today() + timedelta(days=10)
        self.trip = dict(origin='Paris', destination='Rome', start_date=start.isoformat(),
                         end_date=(start + timedelta(days=5)).isoformat(), budget=1500)

    async def test_real_offers_cache_and_correct_one_way_budget(self):
        calls = []
        def handler(request):
            calls.append(request)
            self.assertEqual(request.url.params['type'], '2')
            self.assertEqual(request.url.params['currency'], 'EUR')
            price = 152 if request.url.params['departure_id'] == 'CDG,ORY' else 91
            return httpx.Response(200, json={'best_flights': [{'price': price, 'total_duration': 140,
                'flights': [{'airline': 'Compagnie réelle', 'departure_airport': {'id': 'CDG', 'time': '2026-10-15 10:00'},
                             'arrival_airport': {'id': 'FCO', 'time': '2026-10-15 12:20'}}]}],
                'search_metadata': {'google_flights_url': 'https://www.google.com/travel/flights'}})
        original = httpx.AsyncClient
        with patch.dict(os.environ, {'SERPAPI_API_KEY': 'test'}), patch.object(agent.httpx, 'AsyncClient', side_effect=lambda: original(transport=httpx.MockTransport(handler))):
            result = await agent.execute(self.trip)
            again = await agent.execute(self.trip)
        self.assertEqual(len(calls), 2)
        self.assertEqual(result, again)
        self.assertEqual(result['flights']['aller'][0]['price_kind'], 'observed')
        self.assertEqual(result['flights']['aller'][0]['price_scope'], 'one_way')
        self.assertTrue(result['flights']['aller'][0]['observed_at'])
        budget = budget_summary(TripRequest(**self.trip), {**result, 'stay': [{'total_price_eur': 395}]})
        self.assertEqual(budget['flight_cost_eur'], 243)
        self.assertEqual(budget['estimated_subtotal_eur'], 638)

    async def test_quota_keeps_partial_results_without_simulation(self):
        def handler(request):
            if request.url.params['departure_id'] == 'CDG,ORY':
                return httpx.Response(429)
            return httpx.Response(200, json={'best_flights': [{'price': 91, 'flights': [{'airline': 'ITA'}]}]})
        original = httpx.AsyncClient
        with patch.dict(os.environ, {'SERPAPI_API_KEY': 'test'}), patch.object(agent.httpx, 'AsyncClient', side_effect=lambda: original(transport=httpx.MockTransport(handler))):
            result = await agent.execute(self.trip)
        self.assertFalse(result['flights']['aller'])
        self.assertTrue(result['flights']['retour'])
        self.assertIn('Quota', result['error'])
        self.assertIsNone(budget_summary(TripRequest(**self.trip), result)['flight_cost_eur'])

    async def test_missing_key_and_unknown_city_never_invent_flights(self):
        with patch.dict(os.environ, {'SERPAPI_API_KEY': ''}):
            result = await agent.execute(self.trip)
        self.assertFalse(result['flights']['aller'])
        with patch.dict(os.environ, {'SERPAPI_API_KEY': 'test'}):
            result = await agent.execute({**self.trip, 'destination': 'Unknown'})
        self.assertIn('IATA', result['error'])
        self.assertEqual(agent.airport_id('Fès'), 'FEZ')
        self.assertEqual(agent.airport_id('CDG'), 'CDG')
