import unittest
from unittest.mock import Mock, patch
from launch import wait_for_services


class LaunchTests(unittest.TestCase):
    def test_loading_can_finish_after_old_90_second_limit(self):
        process = Mock()
        process.poll.return_value = None
        response = Mock(status=200)
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        opener = Mock()
        opener.open.side_effect = [OSError("loading"), response]
        with patch("launch.urllib.request.build_opener", return_value=opener), patch("launch.time.monotonic", side_effect=[0, 0, 95, 96, 100]), patch("launch.time.sleep"), patch("builtins.print"):
            wait_for_services([process], [8000], 300)
        self.assertEqual(opener.open.call_count, 2)

    def test_exited_backend_is_reported_immediately(self):
        process = Mock()
        process.poll.return_value = 2
        with self.assertRaisesRegex(RuntimeError, "code 2"):
            wait_for_services([process], [8000], 300)

    def test_timeout_reports_waiting_ports(self):
        with patch("launch.time.monotonic", side_effect=[0, 301]):
            with self.assertRaisesRegex(RuntimeError, "8000"):
                wait_for_services([], [8000], 300)
