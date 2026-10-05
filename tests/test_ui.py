from pathlib import Path
import unittest
from unittest.mock import Mock, patch

import requests
from streamlit.testing.v1 import AppTest


UI_PATH = Path(__file__).resolve().parents[1] / "travel_ui.py"


class InterfaceTests(unittest.TestCase):
    def test_observed_hotel_and_dated_forecast_are_visible(self):
        response = Mock()
        response.json.return_value = {"flights": {"aller": [], "retour": []}, "activities": [],
            "stay": [{"name": "Hôtel réel", "price_per_night_eur": 97, "total_price_eur": 477,
                      "booking_url": "https://www.google.com/travel/hotels"}],
            "weather": {"temperature": "21°C", "daily": [{"date": "2026-10-15", "min_c": 13,
                         "max_c": 22, "rain_probability_pct": 40}], "warnings": ["Dates partiellement disponibles"]}}
        app = AppTest.from_file(str(UI_PATH)).run(timeout=20)
        with patch("requests.post", return_value=response):
            app.button[0].click().run(timeout=20)
        self.assertFalse(app.exception)
        self.assertFalse(app.error)
        self.assertEqual(len(app.get("link_button")), 1)
        self.assertEqual(len(app.dataframe), 1)
        self.assertIn("Dates partiellement disponibles", [item.value for item in app.info])
        self.assertEqual(len(app.get("download_button")), 1)

    def test_real_flights_show_times_and_google_links(self):
        response = Mock()
        flight = {"airline": "Air France", "price": 152, "departure_airport": "CDG",
                  "arrival_airport": "FCO", "departure_time": "2026-10-15 10:00",
                  "arrival_time": "2026-10-15 12:00", "duration": "2h 0min", "stops": 0,
                  "search_url": "https://www.google.com/travel/flights"}
        response.json.return_value = {"flights": {"aller": [flight], "retour": [flight]},
                                      "stay": [], "activities": [], "weather": {}}
        app = AppTest.from_file(str(UI_PATH)).run(timeout=20)
        with patch("requests.post", return_value=response):
            app.button[0].click().run(timeout=20)
        self.assertFalse(app.exception)
        self.assertFalse(app.error)
        self.assertEqual(len(app.get("link_button")), 2)
        self.assertTrue(any("2026-10-15 10:00" in item.value for item in app.markdown))
        self.assertFalse(any("<br>CDG" in item.value for item in app.markdown))
        self.assertEqual(len(app.get("download_button")), 1)

    def test_empty_stay_and_weather_error_do_not_crash(self):
        response = Mock()
        response.json.return_value = {
            "flights": {"aller": [], "retour": []},
            "stay": "Aucun hebergement trouve.", "activities": [],
            "weather": {"error": "Cle meteo manquante"},
        }
        app = AppTest.from_file(str(UI_PATH)).run(timeout=20)
        self.assertFalse(app.exception)
        with patch("requests.post", return_value=response):
            app.button[0].click().run(timeout=20)
        self.assertFalse(app.exception)
        self.assertFalse(app.error)
        self.assertIn("Cle meteo manquante", [warning.value for warning in app.warning])
        self.assertIn("Aucun hebergement trouve.", [info.value for info in app.info])
        response.raise_for_status.assert_called_once()

    def test_http_error_is_reported_before_reading_results(self):
        response = Mock()
        response.raise_for_status.side_effect = requests.HTTPError("Service unavailable")
        app = AppTest.from_file(str(UI_PATH)).run(timeout=20)
        with patch("requests.post", return_value=response):
            app.button[0].click().run(timeout=20)
        self.assertFalse(app.exception)
        self.assertTrue(app.error)
        response.json.assert_not_called()


    def test_invalid_dates_do_not_call_backend(self):
        app = AppTest.from_file(str(UI_PATH)).run(timeout=20)
        app.date_input[1].set_value(app.date_input[0].value)
        with patch("requests.post") as call:
            app.button[0].click().run(timeout=20)
        call.assert_not_called()
        self.assertTrue(app.error)
        self.assertFalse(app.exception)

    def test_summary_removed_and_download_persists_without_new_search(self):
        response = Mock()
        response.json.return_value = {
            "flights": {"aller": [], "retour": []}, "stay": [], "activities": [], "weather": {},
            "summary": "Votre synthèse", "ai": {"status": "disabled", "message": "Clé modèle absente"},
            "budget": {"lodging_per_night_eur": 100, "estimated_subtotal_eur": 600, "within_budget": False},
        }
        app = AppTest.from_file(str(UI_PATH)).run(timeout=20)
        with patch("requests.post", return_value=response):
            app.button[0].click().run(timeout=20)
        self.assertFalse(app.exception)
        self.assertFalse(app.error)
        self.assertFalse(app.metric)
        self.assertNotIn("Clé modèle absente", [info.value for info in app.info])
        self.assertNotIn("Votre synthèse", [markdown.value for markdown in app.markdown])
        self.assertEqual(len(app.get("download_button")), 1)
        with patch("requests.post") as call:
            app.text_input[1].set_value("Paris").run(timeout=20)
        call.assert_not_called()
        self.assertEqual(app.session_state["voyage_result"]["trip"]["destination"], "Rome")
        self.assertEqual(len(app.get("download_button")), 1)
