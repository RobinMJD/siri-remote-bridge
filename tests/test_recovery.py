import socket
import threading
import time
import unittest
from unittest.mock import patch

from healthcheck import healthy
from relay import Link, Sender, transport, validate_config
from webhook_request import send

READY = {
    "available": True,
    "powered": True,
    "bond_present": True,
    "bus_id": "bus1",
    "owner": ":1.0",
}


class RecoveryTests(unittest.TestCase):
    def test_missing_backend_waits_without_pairing(self):
        self.assertEqual(Link().observe({"available": False}), (False, True, "waiting_backend"))

    def test_delayed_backend_recovers(self):
        link = Link()
        link.observe({"available": False})
        self.assertEqual(link.observe(READY), (True, False, "ready"))

    def test_bus_replacement_resets_decoder_even_if_name_is_reused(self):
        link = Link()
        link.observe(READY)
        self.assertEqual(link.observe({**READY, "bus_id": "bus2"}), (True, True, "ready"))

    def test_bluez_restart_resets_decoder(self):
        link = Link()
        link.observe(READY)
        self.assertTrue(link.observe({**READY, "owner": ":1.2"})[1])

    def test_missing_bond_never_launches_decoder(self):
        self.assertEqual(
            Link().observe({**READY, "bond_present": False}), (False, True, "repair_required")
        )

    def test_auth_failure_stays_manual(self):
        link = Link()
        link.repair_required = True
        self.assertEqual(link.observe(READY), (False, True, "repair_required"))

    def test_sleep_is_not_backend_failure(self):
        self.assertEqual(Link().observe({**READY, "connected": False}), (True, False, "ready"))

    def test_healthy_waiting_for_remote(self):
        self.assertTrue(
            healthy({"heartbeat": 100, "worker_alive": True, "phase": "waiting_remote"}, 110)
        )

    def test_stale_or_invalid_heartbeat_fails(self):
        for value in [80, 120, float("nan"), "100"]:
            self.assertFalse(healthy({"heartbeat": value, "worker_alive": True}, 110))

    def test_dead_worker_or_auth_failure_fails(self):
        self.assertFalse(healthy({"heartbeat": 100, "worker_alive": False}, 100))
        self.assertFalse(
            healthy({"heartbeat": 100, "worker_alive": True, "phase": "repair_required"}, 100)
        )

    def test_stale_input_is_dropped(self):
        sent = []
        sender = Sender(lambda button: sent.append(button) or 200)
        sender.submit("mute", 1)
        sender.deliver(sender.pending.get_nowait(), 2)
        self.assertEqual(sent, [])

    def test_disconnect_invalidates_already_dequeued_input(self):
        sent = []
        sender = Sender(lambda button: sent.append(button) or 200)
        sender.submit("suspend", 1)
        item = sender.pending.get_nowait()
        sender.invalidate()
        sender.deliver(item, 1.1)
        self.assertEqual(sent, [])

    def test_queue_is_bounded_and_oldest_burst_dropped(self):
        sender = Sender(lambda _: 200)
        for name in ["up", "down", "left"]:
            sender.submit(name, 1)
        self.assertEqual(sender.pending.qsize(), 1)
        self.assertEqual(sender.pending.get_nowait()[2], "left")

    def test_timeout_is_not_retried(self):
        calls = []

        def fail(button):
            calls.append(button)
            raise TimeoutError()

        sender = Sender(fail)
        sender.submit("mute", 1)
        sender.deliver(sender.pending.get_nowait(), 1.1)
        self.assertEqual(calls, ["mute"])
        self.assertEqual(sender.failures, 1)
        self.assertTrue(sender.pending.empty())

    def test_http_success_and_failure_are_counted(self):
        sender = Sender(lambda _: 200)
        sender.submit("up", 1)
        sender.deliver(sender.pending.get_nowait(), 1.1)
        self.assertEqual(sender.successes, 1)
        sender.transport = lambda _: 503
        sender.submit("up", 2)
        sender.deliver(sender.pending.get_nowait(), 2.1)
        self.assertEqual(sender.failures, 1)
        sender.transport = lambda _: 200
        sender.submit("up", 3)
        sender.deliver(sender.pending.get_nowait(), 3.1)
        self.assertEqual(sender.successes, 2)


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.config = {
            "host": "homeassistant.local",
            "port": 8123,
            "scheme": "http",
            "address": "00:11:22:33:44:55",
            "webhook_id": "a" * 64,
        }

    def test_generic_hostname_and_ip_supported(self):
        for host in ["homeassistant.local", "192.0.2.10", "2001:db8::1"]:
            validate_config({**self.config, "host": host})

    def test_tls_supported(self):
        validate_config({**self.config, "scheme": "https", "port": 443})

    def test_urls_paths_bad_ports_and_schemes_rejected(self):
        for extra in [
            {"host": "https://example.com/path"},
            {"port": True},
            {"port": 0},
            {"port": 65536},
            {"scheme": "ftp"},
            {"scheme": None},
            {"device_id": "../../anything"},
            {"webhook_id": "weak"},
            {"address": "*"},
        ]:
            with self.assertRaises(ValueError):
                validate_config({**self.config, **extra})

    @patch("webhook_request.http.client.HTTPSConnection")
    def test_https_requires_default_certificate_verification(self, connection):
        connection.return_value.getresponse.return_value.status = 200
        send({**self.config, "scheme": "https"}, "wakeup")
        context = connection.call_args.kwargs["context"]
        self.assertTrue(context.check_hostname)
        self.assertEqual(context.verify_mode, 2)

    def test_response_drip_cannot_stall_sender(self):
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen(1)
            listener.settimeout(2)

            def drip():
                try:
                    with listener.accept()[0] as peer:
                        peer.settimeout(2)
                        peer.recv(4096)
                        for byte in b"HTTP/1.1 200 OK\r\n":
                            peer.sendall(bytes([byte]))
                            time.sleep(0.15)
                except (OSError, TimeoutError):
                    pass

            thread = threading.Thread(target=drip, daemon=True)
            thread.start()
            started = time.monotonic()
            status = transport(
                {**self.config, "host": "127.0.0.1", "port": listener.getsockname()[1]},
                "wakeup",
            )
            elapsed = time.monotonic() - started
            self.assertEqual(status, 0)
            self.assertLess(elapsed, 0.8)
            thread.join(timeout=1)

    def test_isolated_request_delivers_one_scoped_command(self):
        received = []
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen(1)
            listener.settimeout(2)

            def reply():
                with listener.accept()[0] as peer:
                    peer.settimeout(2)
                    data = b""
                    while b"\r\n\r\n" not in data:
                        data += peer.recv(4096)
                    headers, body = data.split(b"\r\n\r\n", 1)
                    length = int(
                        next(
                            line.split(b":", 1)[1].strip()
                            for line in headers.split(b"\r\n")
                            if line.lower().startswith(b"content-length:")
                        )
                    )
                    while len(body) < length:
                        body += peer.recv(4096)
                    received.append(headers + b"\r\n\r\n" + body)
                    peer.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n")

            thread = threading.Thread(target=reply, daemon=True)
            thread.start()
            status = transport(
                {**self.config, "host": "127.0.0.1", "port": listener.getsockname()[1]},
                "wakeup",
            )
            thread.join(timeout=1)
            self.assertEqual(status, 200)
            self.assertEqual(len(received), 1)
            self.assertIn(b"POST /api/webhook/" + b"a" * 64, received[0])
            self.assertIn(b'"button": "wakeup"', received[0])


if __name__ == "__main__":
    unittest.main()
