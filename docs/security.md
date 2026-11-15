# Security model

## Privileges

Only BlueZ uses host networking and NET_ADMIN/NET_RAW/NET_BIND_SERVICE for the
Bluetooth/L2CAP control plane. This is a residual host capability boundary, not
full isolation against a malicious BlueZ daemon. No container is privileged;
there is no host D-Bus, Docker socket, uinput, host filesystem or published port.
The decoder/relay is UID 65532, capability-free, no-new-privileges, read-only,
resource-limited. D-Bus allows only root and that UID. The receiver's BlueZ
calls are allowlisted for status, bonded reconnect and HID GATT;
pairing, bond removal and adapter property writes are denied to it. The GATT
write methods remain necessary capabilities on this dedicated adapter. Discovery
is reserved for the explicit root pairing flow; the relay relies on the stored bond.
Restrict the Linux host and physical radio access accordingly.

Host networking means BlueZ inherits the host network namespace. The disabled
network/audio plugins and no public service requirement do not substitute for
a host firewall. Inspect listeners when changing BlueZ/plugins.

The BlueZ image rebuilds Debian trixie's `5.82-1.1` package as
`5.82-1.1+bridge1`. The only source change backports BlueZ's device-name length
fix for CVE-2026-80186; that parser is reachable during a bonded connection as
well as discovery. The build pins the Debian source files by SHA-256 and runs
BlueZ's EIR parser tests, including a 253-byte malformed name and a maximum
valid name. It stops if Debian replaces the base `5.82-1.1` package, so a later
security release is not silently overwritten by this backport. A2DP and AVRCP
remain disabled, so their reported BlueZ parser flaws are outside this
deployment's active plugins. A package scanner may still list CVE-2026-80186
because this project version is not a Debian security
release; the applied source patch and build tests are the evidence for this
backport. Other BlueZ and system-library findings require separate assessment.
No software patch eliminates the host capability or radio trust boundary.

## Secrets and trust

The random webhook is a **scoped credential**. Anyone obtaining it with LAN
access can imitate this remote's allowed commands. The device marker/timestamp
are validation, not independent authentication. HTTP on a LAN can be observed
or tampered with: use verified HTTPS when available or opt into HTTP only on a
trusted LAN/VLAN. The setup helper requires an explicit transport choice and
acknowledgement for HTTP. Do not publish the
webhook or relax local-only checks behind an external proxy to bypass routing.

Never commit `.env`, `private/`, HA secrets or Bluetooth bond files. An adapter
bond contains cryptographic material. HA admin traces can expose resolved
webhook IDs; redact them before sharing screenshots/exports. Decoder stdout
may contain raw touch/audio reports internally; the wrapper discards them and
only logs connection state and delivered action metadata, not those payloads.

## Failure and updates

No automatic re-pairing, blanket Bluetooth reset, bond deletion, host service
restart or broad token fallback is allowed. A bad bond is intentionally manual.
No command is retried after an ambiguous HTTP result. Each webhook request is
isolated in a child process; the parent terminates it when its 400 ms wait
expires. Startup and termination add some overhead, and a timed-out request
may have reached Home Assistant even if its response was lost. Power sleep is a
deliberate one-second hold; a short press opens the native power menu or wakes a sleeping
device. It never confirms the highlighted shutdown item automatically.

Base images, BlueZ source archives, GitHub Actions and decoder source are
pinned. apt upgrades and packages come from signed Debian repositories at
build time; Cargo uses the upstream lockfile. This improves auditability, not
bit-for-bit reproducibility or a guarantee that the pins remain patched. Review
dependency PRs, rebuild with current security packages, scan images, and repeat
hardware tests before rollout.

Back up private state encrypted and access-controlled. Restore only to the same
adapter identity where possible; a replacement radio normally requires deliberate
re-pairing. Do not use this project for security-critical controls.
