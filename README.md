# Siri Remote Bridge

[Resume en francais](README.fr.md)

Use a paired Siri Remote through Linux Bluetooth to control Apple TV over your
network, via Home Assistant. Useful when Apple TV is hidden in furniture or
outside reliable Bluetooth range: place the receiver near the remote instead.

```text
Siri Remote -- BLE --> Linux receiver -- scoped webhook --> Home Assistant
                       private BlueZ                       Apple TV over LAN
                                                          optional soundbar mute
```

**Status: early release, tested on one real installation.** This is not a
complete replacement for Apple's remote stack. No Siri microphone forwarding,
swipe gestures or double-clicks are provided. A real
NUC cold reboot and extended unattended soak remain qualification gates, not
claims established by unit tests. See [hardware](docs/hardware.md) and the
[validation matrix](docs/validation.md).

## Requirements

- Linux with working BlueZ-compatible Bluetooth LE hardware and vendor firmware.
- Docker Engine and Compose v2, with permission to run these containers.
- One Bluetooth adapter dedicated to this bridge; do not share it with another
  bluetoothd, Home Assistant Bluetooth, audio peripherals or a host session.
- Home Assistant with Apple TV integration already paired normally.
- A spare Siri Remote: pairing moves it away from its previous Apple TV.
- A trusted private LAN; HTTP webhook traffic is not encrypted. Verified HTTPS
  is supported if your HA endpoint and routing allow local-only webhooks.

The Linux receiver may be a mini-PC, an existing VM with USB passthrough or
another BlueZ-capable Linux board. Home Assistant may live elsewhere. No extra
VM is required, and the relay publishes no port or general HA API credential.

## Setup

1. Clone this repository and build from a reviewed tag/commit:

   ```sh
   git clone https://github.com/RobinMJD/siri-remote-bridge.git
   cd siri-remote-bridge
   docker compose build bluez relay
   ```

2. Prepare persistent directories. Do not place `private/` on a shared or
   publicly served directory. For a system install, set `STATE_DIRECTORY` in
   `.env` to an absolute local path before starting Docker Compose.

   ```sh
   sudo install -d -m 0700 private private/bluetooth
   sudo install -d -m 0755 private/bus private/secrets
   docker compose up -d bluez
   ```

3. Pair **once**, deliberately. Bring the spare remote within about 50 cm of the
   adapter. Hold Back/Menu + Volume Up for about five seconds. Run the pairing
   command as root on this **private bus**, never with host D-Bus or privileged
   Docker access. The temporary container has no persistent restart policy.

   ```sh
   docker compose run --rm --no-deps --user 0:0 \
     --entrypoint /usr/local/bin/siri-remote relay pair
   ```

   Note the bonded **identity address**, not the rotating advertisement address.
   Exit if another remote is selected. Normal unattended operation cannot pair
   or remove bonds. See [pairing recovery](docs/operations.md).

4. Generate a random webhook and private configuration. Substitute your bonded
   identity and HA hostname. The helper refuses existing configuration.

   ```sh
   sudo python3 configure.py --host homeassistant.local --port 8123 \
     --address AA:BB:CC:DD:EE:FF --state-dir private
   ```

   With a custom `STATE_DIRECTORY`, use that same path with `--state-dir`.
   Supported JSON settings are documented in [configuration](docs/configuration.md).
   No secret is printed. Transfer `private/home-assistant-secret.yaml` securely
   into HA's `secrets.yaml`; do not put it in Git or a public issue.

5. Copy [examples/home-assistant.yaml](examples/home-assistant.yaml) to
   `/config/siri_remote_bridge.yaml`, change its fixed Apple TV/soundbar entity
   IDs, and add this separate labeled include to `configuration.yaml`:

   ```yaml
   automation siri_remote_bridge: !include siri_remote_bridge.yaml
   ```

   Keep any existing `automation: !include automations.yaml` unchanged. This
   separate include avoids versions of HA's UI editor that cannot resolve
   `!secret` in the UI-managed list. Run HA's configuration check, then reload
   **Automations** without restarting HA. Never expose this webhook publicly or
   disable SSO/WAF to make it work. Keep `local_only: true`.

6. Start and verify:

   ```sh
   docker compose up -d
   docker compose ps
   docker compose logs --tail 30 relay
   docker compose exec relay cat /run/siri-remote/status.json
   ```

   `connected` means the decoder subscribed successfully. `waiting_remote` is
   normal while the remote is asleep/out of range. Test actual buttons; an HTTP
   200 alone does not prove that HA conditions passed or a TV reacted.

## Buttons

| Input | Default event / example behavior |
| --- | --- |
| Arrows | Navigation; repeats after 350 ms at 150 ms intervals, bounded to 3 s |
| Select tap / hold 650 ms | Click on release / native held-Select context menu |
| Back tap / hold 650 ms | Back / native held-menu to Home Screen |
| TV/Home tap / hold 650 ms | Home / Control Centre |
| Play/Pause | HA media play/pause |
| Volume Up/Down | Apple TV network volume; audio-path dependent |
| Mute | Optional direct soundbar mute via HA |
| Power tap / hold 1 s | Power-focused menu when awake, wake when asleep / sleep once |

Short Power opens the native power-focused shortcut without confirming sleep;
it wakes instead when HA reports the device asleep. Long Power explicitly
sleeps once; release does not emit a second command. It is not a blind power
toggle. TV/receiver power depends on existing HDMI-CEC; its settings are unchanged.
Select taps wait for release so holding cannot first open/play the highlighted
item. The HA example must be updated alongside the relay for `select_hold` and
`power_menu`; a receiver update alone is insufficient. Native held-input adds
some latency beyond the bridge's tap/hold threshold.

## Boot and reconnect

Enable Docker on Linux (`sudo systemctl enable docker` on systemd systems) and,
for a VM, its hypervisor autostart. Both services use `unless-stopped`: they
restart after crashes or daemon/guest reboot, but respect an intentional stop.
Compose readiness helps initial startup; **runtime** recovery also handles
replaced D-Bus/BlueZ, delayed hardware and ordinary remote reconnects. No daemon
restart or reboot of other services is used as a repair mechanism.

An idle remote is not unhealthy. A deleted/invalid bond requires an operator,
not unattended adoption of the nearest remote. No buffered command is replayed
after reconnection. See [operations](docs/operations.md) for diagnostics,
backup/restore, updates, rollback, monitoring and tests.

## Development and security

- [Architecture and configuration](docs/configuration.md)
- [Security model](docs/security.md)
- [Hardware compatibility](docs/hardware.md)
- [Validation](docs/validation.md)
- [Contributing](CONTRIBUTING.md), [changelog](CHANGELOG.md)
- [GPL-3.0-or-later license](LICENSE), [upstream attribution](THIRD_PARTY.md)

No cloud service, account subscription, prebuilt image registry or telemetry
service is required. Builds need internet; normal control is local. Apple TV
apps themselves may still require internet. Dependency updates are proposed for
review, not silently deployed to hardware.
