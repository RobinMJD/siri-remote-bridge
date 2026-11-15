import contextlib
import io
import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import collect_metrics
import configure


class ToolsTests(unittest.TestCase):
    def test_power_menu_is_native_shortcut_without_shutdown_confirmation(self):
        source = (Path(__file__).resolve().parents[1] / "examples/home-assistant.yaml").read_text()
        self.assertIn("'power_menu'", source.split("actions:", 1)[0])
        branch = source.split("trigger.json.button in ['wakeup','power_menu']", 1)[1]
        branch = branch.split("- conditions:", 1)[0]
        self.assertIn("else 'control_center'", branch)
        self.assertIn("power_needs_wake", branch)
        self.assertNotIn("command: select", branch)
        self.assertNotIn("command: suspend", branch)

    def test_example_select_hold_uses_native_input_not_a_regular_click(self):
        source = (Path(__file__).resolve().parents[1] / "examples/home-assistant.yaml").read_text()
        self.assertIn("'select_hold'", source.split("actions:", 1)[0])
        branch = source.split("trigger.json.button == 'select_hold'", 1)[1]
        branch = branch.split("- conditions:", 1)[0]
        self.assertIn("command: select, hold_secs: 1", branch)
        self.assertIn("num_repeats: 1", branch)

    def test_example_freshness_allows_small_clock_skew_but_keeps_old_input_expiry(self):
        source = (Path(__file__).resolve().parents[1] / "examples/home-assistant.yaml").read_text()
        match = re.search(r"and (-?[\d.]+) <= as_timestamp\(now\(\)\).*? < ([\d.]+)", source)
        self.assertIsNotNone(match)
        lower, upper = map(float, match.groups())
        self.assertEqual((lower, upper), (-0.25, 1.0))
        for age in [-0.008, 0, 0.99]:
            self.assertTrue(lower <= age < upper)
        for age in [-0.251, -1, 1, 5, float("nan")]:
            self.assertFalse(lower <= age < upper)

    def test_home_hold_example_uses_native_hold_not_control_center_shortcut(self):
        example = (Path(__file__).resolve().parents[1] / "examples/home-assistant.yaml").read_text()
        branch = example.split("trigger.json.button == 'control_center'", 1)[1]
        branch = branch.split("- conditions:", 1)[0]
        self.assertIn("command: home, hold_secs: 1", branch)
        self.assertIn("num_repeats: 1", branch)
        self.assertNotIn("command: control_center", branch)

    @patch("collect_metrics.command")
    def test_metrics_are_liveness_not_idle_activity(self, command):
        command.side_effect = ['{"Running":true,"Health":{"Status":"healthy"}}'] * 2 + [
            json.dumps(
                {
                    "heartbeat": 100,
                    "worker_alive": True,
                    "phase": "waiting_remote",
                    "backend_ready": True,
                    "bond_present": True,
                    "remote_connected": False,
                }
            )
        ]
        with patch("collect_metrics.time.monotonic", return_value=101):
            metrics = collect_metrics.collect("bridge")
        self.assertEqual(metrics['component_up{component="relay"}'], 1)
        self.assertEqual(metrics["remote_connected"], 0)
        self.assertEqual(metrics["heartbeat_fresh"], 1)

    @patch("collect_metrics.command")
    def test_missing_container_has_zero_metrics(self, command):
        command.side_effect = OSError()
        metrics = collect_metrics.collect("bridge")
        self.assertEqual(metrics["backend_ready"], 0)
        self.assertEqual(metrics["heartbeat_fresh"], 0)

    @patch("collect_metrics.command")
    def test_corrupt_status_cannot_emit_nonfinite_metrics(self, command):
        for raw in [
            "[]",
            '{"heartbeat":"oops","http_failures":-1}',
            '{"heartbeat":NaN,"http_successes":"secret"}',
        ]:
            command.side_effect = ["{}", "{}", raw]
            metrics = collect_metrics.collect("bridge")
            self.assertEqual(metrics["heartbeat_fresh"], 0)
            self.assertTrue(all(type(value) is int for value in metrics.values()))

    @patch("configure.os.fchown")
    @patch("configure.os.geteuid", return_value=0)
    def test_configure_creates_private_random_matching_secret(self, _uid, _chown):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            args = [
                "configure.py",
                "--host",
                "homeassistant.local",
                "--address",
                "AA:BB:CC:DD:EE:FF",
                "--state-dir",
                str(root),
            ]
            with patch("sys.argv", args), contextlib.redirect_stdout(io.StringIO()):
                configure.main()
            config_file = root / "secrets/ha_webhook.json"
            config = json.loads(config_file.read_text())
            self.assertEqual(len(config["webhook_id"]), 64)
            self.assertEqual(config_file.stat().st_mode & 0o777, 0o400)
            self.assertIn(config["webhook_id"], (root / "home-assistant-secret.yaml").read_text())
            with (
                patch("sys.argv", args),
                contextlib.redirect_stderr(io.StringIO()),
                self.assertRaises(SystemExit),
            ):
                configure.main()
            self.assertEqual(config, json.loads(config_file.read_text()))


if __name__ == "__main__":
    unittest.main()
