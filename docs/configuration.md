# Architecture and configuration

## Boundaries

`bluez` owns a private D-Bus and the single passed-through/host Bluetooth
adapter. Bond files persist in `STATE_DIRECTORY/bluetooth`. `relay` runs as
UID/GID 65532 and launches the pinned Rust decoder as a child. Only fresh button
frames are translated into bounded commands. Python's standard library handles
HTTP; Debian's python3-dbus package reads structured BlueZ status.

Hardware independence is at the Linux/BlueZ boundary: the bridge does not
hard-code a NUC, Intel USB ID, MAC, LAN address, HA entity or Sonos requirement.
The **input protocol** remains Siri Remote HID as understood by the pinned
upstream decoder. Arbitrary brands of remotes are not automatically supported.
Add a different input adapter only with explicit protocol parsing/tests; keep
the bounded sender and HA allowlist intact.

## JSON configuration

`STATE_DIRECTORY/secrets/ha_webhook.json`, read-only by UID 65532:

| Field | Meaning |
| --- | --- |
| `host` | HA hostname, IPv4 or unbracketed IPv6; no scheme/path/userinfo |
| `port` | Integer 1-65535, e.g. 8123 or 443 |
| `scheme` | `http` (default) or `https`, with normal certificate verification |
| `device_id` | Fixed marker, default `siri_remote_bridge`; match the HA condition |
| `webhook_id` | Random 64-hex-character secret generated locally |
| `address` | Uppercase bonded identity MAC; not the random advertisement |

No URL, target entity or service name comes from untrusted button frames.
Destination changes require editing the root-controlled JSON and recreating
the relay. TLS validation cannot be switched off. No authentication token for
the full HA API is used. NTP synchronization is needed for input freshness.

The supplied HA YAML is a **template**, not an installer. Set the fixed targets
to existing entities. You can map another sound system by replacing its mute
branch with a narrow supported action. Keep allowed events, marker, timestamp,
POST restriction, local-only behavior and fixed targets.

`remote.turn_on` reconnects HA's Apple TV controller; it is not actual power.
The example uses `remote.send_command` `wakeup`/`suspend` for real power.
Held Back uses `menu` with `hold_secs: 1`; upstream Companion `top_menu` was not
supported on the tested installation. Mute via Companion was unsupported there,
so the example uses an optional soundbar entity instead.

## Recovery state machine

- Every two seconds read the private bus ID, BlueZ owner, adapter and bonded
  device. A replaced bus/BlueZ invalidates the old decoder and queued input.
- If the backend is absent/unpowered, wait without pairing or sending commands.
- A missing bond or attempted authentication fallback enters manual repair.
  D-Bus policy independently denies Pair and RemoveDevice to UID 65532.
- The upstream decoder reconnects only to the configured identity. If it exits
  or stalls before notification subscription for 90 seconds, relaunch it.
- A link drop clears deferred holds and queued commands. A disconnected remote
  is not restarted merely because no button was pressed.
- The separate command worker bounds HTTP operations to 400 ms, expires queued
  input after 500 ms, and never retries possibly delivered toggles.
- Status is atomically written to tmpfs. Docker liveness detects a stale loop
  or dead worker, not an absence of button activity. Docker **healthchecks do
  not themselves restart containers**: recovery is implemented by the process
  supervisor and exit/restart policy. There is no hidden global autoheal agent.

One already-issued HTTP request cannot be recalled during a disconnect. The
bridge drops everything it has not yet issued and never retries that request.
