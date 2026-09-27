from pathlib import Path
import unittest
from unittest.mock import Mock, patch

import requests
from streamlit.testing.v1 import AppTest


UI_PATH = Path(__file__).resolve().parents[1] / "travel_ui.py"


class InterfaceTests(unittest.TestCase):
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
