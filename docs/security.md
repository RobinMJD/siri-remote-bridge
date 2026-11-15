# Security model

## Privileges

Only BlueZ uses host networking and NET_ADMIN/NET_RAW/NET_BIND_SERVICE for the
Bluetooth/L2CAP control plane. This is a residual host capability boundary, not
full isolation against a malicious BlueZ daemon. No container is privileged;
there is no host D-Bus, Docker socket, uinput, host filesystem or published port.
The decoder/relay is UID 65532, capability-free, no-new-privileges, read-only,
resource-limited. D-Bus allows only root and that UID and denies it pairing and
bond removal. Restrict the Linux host and physical radio access accordingly.

Host networking means BlueZ inherits the host network namespace. The disabled
network/audio plugins and no public service requirement do not substitute for
a host firewall. Inspect listeners when changing BlueZ/plugins.

## Secrets and trust

The random webhook is a **scoped credential**. Anyone obtaining it with LAN
access can imitate this remote's allowed commands. The device marker/timestamp
are validation, not independent authentication. HTTP on a LAN can be observed
or tampered with: use a trusted LAN/VLAN or verified HTTPS. Do not publish the
webhook or relax local-only checks behind an external proxy to bypass routing.

Never commit `.env`, `private/`, HA secrets or Bluetooth bond files. An adapter
bond contains cryptographic material. HA admin traces can expose resolved
webhook IDs; redact them before sharing screenshots/exports. Decoder stdout
may contain raw touch/audio reports internally; the wrapper discards them and
only logs connection state and delivered action metadata, not those payloads.

## Failure and updates

No automatic re-pairing, blanket Bluetooth reset, bond deletion, host service
restart or broad token fallback is allowed. A bad bond is intentionally manual.
No command is retried after an ambiguous HTTP result. Power sleep is a deliberate
one-second hold; a short press opens the native power menu or wakes a sleeping
device. It never confirms the highlighted shutdown item automatically.

Base images, GitHub Actions and decoder source are pinned. apt packages come
from the signed Debian repositories at build time; Cargo uses the upstream
lockfile. This improves auditability, not bit-for-bit reproducibility or a
guarantee that the pins remain patched. Review dependency PRs, rebuild with
current security packages, scan images, and repeat hardware tests before rollout.

Back up private state encrypted and access-controlled. Restore only to the same
adapter identity where possible; a replacement radio normally requires deliberate
re-pairing. Do not use this project for security-critical controls.
