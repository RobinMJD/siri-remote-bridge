"""Forward fresh button edges from one bonded remote to a scoped HA webhook."""

import datetime
import http.client
import json
import math
import os
import pathlib
import queue
import re
import selectors
import signal
import ssl
import subprocess
import threading
import time

from bluez_status import probe

BUTTONS = {
    0x0001: "home",
    0x0002: "volume_up",
    0x0004: "volume_down",
    0x0008: "select",
    0x0010: "power_menu",
    0x0040: "menu",
    0x0080: "mute",
    0x0100: "play_pause",
    0x0200: "up",
    0x0400: "right",
    0x0800: "down",
    0x1000: "left",
}
REPEATING = {"up", "down", "left", "right", "volume_up", "volume_down"}
DEFERRED = {
    0x0001: ("home", "control_center"),
    0x0008: ("select", "select_hold"),
    0x0040: ("menu", "menu_hold"),
    0x0010: ("power_menu", "suspend"),
}
HOLD_SECONDS = 0.65
HOLD_THRESHOLDS = {0x0008: 0.25, 0x0010: 1.0}
REPORT = re.compile(r"^(\S+) input report_id=0xFB raw=([0-9a-fA-F]{2}) ([0-9a-fA-F]{2}) \|")
MAX_AGE = 0.5


def parse_report(line, wall_time):
    match = REPORT.match(line)
    if not match:
        return None
    try:
        stamp = datetime.datetime.fromisoformat(match[1].replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None
    if not math.isfinite(stamp) or not -0.25 <= wall_time - stamp <= MAX_AGE:
        return None
    return int(match[2], 16) | (int(match[3], 16) << 8)


class Buttons:
    def __init__(self):
        self.clear()

    def clear(self):
        self.mask = 0
        self.held = {}
        self.deferred = {}

    def update(self, mask, now):
        released = self.mask & ~mask
        pressed = mask & ~self.mask
        self.mask = mask
        self.held = {bit: value for bit, value in self.held.items() if mask & bit}
        commands = []
        for bit, (started, sent) in list(self.deferred.items()):
            if released & bit:
                if not sent:
                    threshold = HOLD_THRESHOLDS.get(bit, HOLD_SECONDS)
                    commands.append(DEFERRED[bit][1 if now - started >= threshold else 0])
                del self.deferred[bit]
        for bit, button in BUTTONS.items():
            if pressed & bit:
                if bit in DEFERRED:
                    self.deferred[bit] = (now, False)
                    continue
                commands.append(button)
                if button in REPEATING:
                    self.held[bit] = (now, now + 0.35)
        return commands

    def repeat(self, now):
        commands = []
        for bit, (started, sent) in list(self.deferred.items()):
            if not sent and now - started >= HOLD_THRESHOLDS.get(bit, HOLD_SECONDS):
                commands.append(DEFERRED[bit][1])
                self.deferred[bit] = (started, True)
        for bit, (started, due) in list(self.held.items()):
            # A missing release must not keep navigating indefinitely.
            if now - started >= 3:
                del self.held[bit]
            elif now >= due:
                commands.append(BUTTONS[bit])
                self.held[bit] = (started, now + 0.15)
        return commands


class Sender:
    """Bounded, expiring commands; a new link invalidates previous queued input."""

    def __init__(self, transport):
        self.transport = transport
        self.pending = queue.Queue(maxsize=2)
        self.lock = threading.Lock()
        self.generation = 0
        self.successes = self.failures = 0
        self.last_success = 0

    def invalidate(self):
        with self.lock:
            self.generation += 1
            self._drain()

    def _drain(self):
        while True:
            try:
                self.pending.get_nowait()
            except queue.Empty:
                return

    def submit(self, button, now):
        with self.lock:
            if self.pending.full():
                self._drain()
            self.pending.put_nowait((self.generation, now, button))

    def deliver(self, item, now):
        generation, created, button = item
        with self.lock:
            if generation != self.generation or not 0 <= now - created <= MAX_AGE:
                return
        # No retry, including ambiguous timeouts: input must never replay later.
        try:
            status = self.transport(button)
        except (OSError, http.client.HTTPException):
            status = 0
        with self.lock:
            if 200 <= status < 300:
                self.successes += 1
                self.last_success = time.time()
            else:
                self.failures += 1

    def run(self, stop):
        while not stop.is_set():
            try:
                item = self.pending.get(timeout=0.1)
            except queue.Empty:
                continue
            self.deliver(item, time.monotonic())


def validate_config(config):
    if not isinstance(config, dict):
        raise ValueError("Configuration must be an object")
    host = config.get("host")
    if not isinstance(host, str) or not re.fullmatch(r"[a-zA-Z0-9_.:-]{1,253}", host):
        raise ValueError("Use a hostname or IP address, not a URL")
    port = config.get("port")
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError("Invalid endpoint port")
    if config.get("scheme", "http") not in ("http", "https"):
        raise ValueError("Only HTTP or verified HTTPS is supported")
    if not isinstance(config.get("device_id", "siri_remote_bridge"), str) or not re.fullmatch(
        r"[a-zA-Z0-9_-]{1,64}", config.get("device_id", "siri_remote_bridge")
    ):
        raise ValueError("Invalid device identifier")
    if not re.fullmatch(r"[0-9a-f]{64}", config["webhook_id"]):
        raise ValueError("Invalid webhook identifier")
    if not re.fullmatch(r"(?:[0-9A-F]{2}:){5}[0-9A-F]{2}", config["address"]):
        raise ValueError("Invalid bonded remote address")


def transport(config, button):
    body = json.dumps(
        {
            "device": config.get("device_id", "siri_remote_bridge"),
            "button": button,
            "sent_at": time.time(),
        }
    )
    if config.get("scheme", "http") == "https":
        connection = http.client.HTTPSConnection(
            config["host"], config["port"], timeout=0.4, context=ssl.create_default_context()
        )
    else:
        connection = http.client.HTTPConnection(config["host"], config["port"], timeout=0.4)
    started = time.monotonic()
    try:
        connection.request(
            "POST",
            "/api/webhook/" + config["webhook_id"],
            body=body,
            headers={"Content-Type": "application/json"},
        )
        status = connection.getresponse().status
        print(
            json.dumps(
                {
                    "button": button,
                    "http_status": status,
                    "elapsed_ms": round((time.monotonic() - started) * 1000),
                }
            ),
            flush=True,
        )
        return status
    except (OSError, http.client.HTTPException) as error:
        print(
            json.dumps({"button": button, "error": type(error).__name__, "retry": False}),
            flush=True,
        )
        raise
    finally:
        connection.close()


class Link:
    """Separate radio sleep from a stale bus, stalled decoder or invalid bond."""

    def __init__(self):
        self.identity = None
        self.repair_required = False

    def observe(self, info):
        identity = (info.get("bus_id"), info.get("owner"))
        replaced = self.identity is not None and identity != self.identity
        self.identity = identity if info.get("available") else None
        ready = bool(info.get("available") and info.get("powered") and info.get("bond_present"))
        if self.repair_required:
            return False, True, "repair_required"
        if not info.get("available") or not info.get("powered"):
            return False, True, "waiting_backend"
        if not info.get("bond_present"):
            return False, True, "repair_required"
        return ready, replaced, "ready"


def write_status(status):
    path = pathlib.Path("/run/siri-remote/status.json")
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(status) + "\n")
    tmp.replace(path)


def main():
    with open("/run/secrets/ha_webhook.json") as handle:
        config = json.load(handle)
    validate_config(config)
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    sender = Sender(lambda button: transport(config, button))
    worker = threading.Thread(target=sender.run, args=(stop,), daemon=True)
    worker.start()
    buttons = Buttons()
    link = Link()
    selector = selectors.DefaultSelector()
    process = None
    connected = False
    buffer = b""
    probe_at = child_started = next_start = 0
    previous_phase = None
    info = {}
    reconnects = 0

    def reset_input():
        buttons.clear()
        sender.invalidate()

    def stop_child():
        nonlocal process, connected, buffer
        reset_input()
        connected = False
        buffer = b""
        if process is not None:
            selector.unregister(process.stdout)
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=2)
            process.stdout.close()
            process = None

    print("RELAY_START bonded-only recovery enabled; microphone ignored", flush=True)
    try:
        while not stop.is_set():
            now = time.monotonic()
            if not worker.is_alive():
                raise RuntimeError("Command worker stopped")
            if now >= probe_at:
                try:
                    info = probe(config["address"])
                except Exception:
                    info = {"available": False}
                ready, reset, phase = link.observe(info)
                if reset:
                    stop_child()
                if connected and not info.get("connected"):
                    connected = False
                    reset_input()
                if process is not None and (
                    process.poll() is not None or (not connected and now - child_started > 90)
                ):
                    stop_child()
                    next_start = now + 2
                if ready and process is None and now >= next_start:
                    process = subprocess.Popen(
                        [
                            "/usr/local/bin/siri-remote",
                            "events",
                            "--address",
                            config["address"],
                            "--reconnect-delay",
                            "2",
                        ],
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                    )
                    selector.register(process.stdout, selectors.EVENT_READ)
                    child_started = now
                if ready:
                    phase = "connected" if connected else "waiting_remote"
                if phase != previous_phase:
                    print("RELAY_STATE " + phase, flush=True)
                    previous_phase = phase
                with sender.lock:
                    counters = {
                        "http_successes": sender.successes,
                        "http_failures": sender.failures,
                        "http_last_success": sender.last_success,
                    }
                write_status(
                    {
                        "heartbeat": time.monotonic(),
                        "worker_alive": worker.is_alive(),
                        "phase": phase,
                        "backend_ready": bool(info.get("powered")),
                        "bond_present": bool(info.get("bond_present")),
                        "remote_connected": connected,
                        "reconnects": reconnects,
                        "child_pid": process.pid if process else None,
                        **counters,
                    }
                )
                probe_at = time.monotonic() + 2
            if process is not None:
                for key, _ in selector.select(timeout=0.03):
                    chunk = os.read(key.fileobj.fileno(), 65536)
                    if not chunk:
                        # EOF is a disconnect too: do not let a deferred hold
                        # fire during the next backend poll interval.
                        stop_child()
                        probe_at = 0
                        next_start = time.monotonic() + 2
                        break
                    buffer += chunk
                    lines = buffer.split(b"\n")
                    buffer = lines.pop()[-4096:]
                    for raw in lines:
                        line = raw.decode("utf-8", "replace")
                        if "Scanning for " in line or "pairing-mode remote" in line:
                            print(
                                "RELAY_REFUSED automatic re-pairing; manual repair required",
                                flush=True,
                            )
                            link.repair_required = True
                            stop_child()
                            probe_at = 0
                            break
                        if "Disconnected" in line or "Connection failed" in line:
                            connected = False
                            reset_input()
                            child_started = time.monotonic()
                        if "Notifications enabled; waiting for events" in line:
                            reset_input()
                            connected = True
                            reconnects += 1
                            print("RELAY_CONNECTED", flush=True)
                        mask = parse_report(line, time.time())
                        if mask is not None and connected:
                            for button in buttons.update(mask, time.monotonic()):
                                sender.submit(button, time.monotonic())
            else:
                stop.wait(0.1)
            if connected:
                for button in buttons.repeat(time.monotonic()):
                    sender.submit(button, time.monotonic())
    finally:
        stop.set()
        stop_child()
        selector.close()
        worker.join(timeout=1)


if __name__ == "__main__":
    main()
