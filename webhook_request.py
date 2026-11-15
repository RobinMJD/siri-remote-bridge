"""One isolated webhook request. The parent enforces the wait limit."""

import http.client
import json
import ssl
import sys
import time


def send(config, button):
    body = json.dumps(
        {
            "device": config.get("device_id", "siri_remote_bridge"),
            "button": button,
            "sent_at": time.time(),
        }
    )
    if config["scheme"] == "https":
        connection = http.client.HTTPSConnection(
            config["host"], config["port"], timeout=0.4, context=ssl.create_default_context()
        )
    else:
        connection = http.client.HTTPConnection(config["host"], config["port"], timeout=0.4)
    try:
        connection.request(
            "POST",
            "/api/webhook/" + config["webhook_id"],
            body=body,
            headers={"Content-Type": "application/json"},
        )
        return connection.getresponse().status
    finally:
        connection.close()


if __name__ == "__main__":
    try:
        status = send(json.load(sys.stdin), sys.argv[1])
    except (OSError, http.client.HTTPException, ValueError, KeyError, IndexError):
        sys.exit(1)
    print(json.dumps({"status": status}))
