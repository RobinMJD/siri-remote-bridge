"""Liveness, not activity: an idle/asleep remote must not cause restart loops."""

import json
import math
import pathlib
import sys
import time


def healthy(status, now):
    beat = status.get("heartbeat", -1)
    return (
        isinstance(beat, (int, float))
        and math.isfinite(beat)
        and 0 <= now - beat < 15
        and status.get("worker_alive") is True
        and status.get("phase") != "repair_required"
    )


if __name__ == "__main__":
    try:
        status = json.loads(pathlib.Path("/run/siri-remote/status.json").read_text())
        ok = healthy(status, time.monotonic())
    except (OSError, ValueError):
        ok = False
    sys.exit(0 if ok else 1)
