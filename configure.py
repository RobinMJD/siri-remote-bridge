"""Create private state once. Never silently rotate a webhook or replace a bond."""

import argparse
import json
import os
import secrets
from pathlib import Path

from relay import validate_config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", type=int, default=8123)
    parser.add_argument("--scheme", choices=["http", "https"], required=True)
    parser.add_argument(
        "--trusted-lan-http",
        action="store_true",
        help="Acknowledge that HTTP reveals the scoped webhook secret on its LAN route",
    )
    parser.add_argument(
        "--address", required=True, help="Bonded identity address, not rotating advertisement"
    )
    parser.add_argument("--device-id", default="siri_remote_bridge")
    parser.add_argument("--state-dir", type=Path, default=Path("private"))
    args = parser.parse_args()
    if args.scheme == "http" and not args.trusted_lan_http:
        parser.error("HTTP requires --trusted-lan-http; prefer verified HTTPS")
    if args.scheme == "https" and args.trusted_lan_http:
        parser.error("--trusted-lan-http is only for HTTP")
    if os.geteuid() != 0:
        parser.error("Run as root to protect bond data and set UID 65532 secret ownership")
    config = {
        "host": args.host,
        "port": args.port,
        "scheme": args.scheme,
        "address": args.address.upper(),
        "device_id": args.device_id,
        "webhook_id": secrets.token_hex(32),
    }
    validate_config(config)
    root = args.state_dir.resolve()
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    if root.stat().st_mode & 0o077:
        parser.error("State directory must be private (chmod 0700)")
    for name, mode in [("bus", 0o755), ("bluetooth", 0o700), ("secrets", 0o755)]:
        (root / name).mkdir(mode=mode, exist_ok=True)
    target = root / "secrets/ha_webhook.json"
    secret = root / "home-assistant-secret.yaml"
    if target.exists() or target.is_symlink() or secret.exists() or secret.is_symlink():
        parser.error(
            "Configuration exists; back it up and edit deliberately instead of rotating it"
        )
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o400)
    with os.fdopen(fd, "w") as handle:
        json.dump(config, handle, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
        os.fchown(handle.fileno(), 65532, 65532)
    fd = os.open(secret, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as handle:
        handle.write("siri_remote_bridge_webhook: " + config["webhook_id"] + "\n")
    print(
        "Private configuration created. Transfer home-assistant-secret.yaml securely to HA secrets.yaml."
    )


if __name__ == "__main__":
    main()
