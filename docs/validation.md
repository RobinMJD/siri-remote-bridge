# Validation scope

Current suite: 61 unit/contract tests. Center Select now has deferred tap/hold
handling and short Power has a separate native menu/wake mapping. These new
behaviors need a physical app/menu check in addition to software tests; do not
interpret older prototype button acceptance as acceptance of this update.

Initial software suite: 51 unit/contract tests covering button mapping and hold
thresholds, bounded repeats, fresh/stale reports, disconnect queue generations,
backend replacement, missing bonds, manual authentication recovery, worker
liveness, timeout/no-retry behavior, TLS validation, private configuration,
metrics corruption handling and container policies.
CI repeats on Python 3.11, 3.13 and 3.14 and builds/runs the Linux image tests.
The native Home-hold example adds one regression contract (52 tests total).

Pre-hardening physical prototype on the hardware described in hardware.md:

- Navigation and selection confirmed by the owner.
- Home hold opens Control Centre; Back hold returns Home without an initial
  Back tap; both confirmed by the owner.
- Direct soundbar mute verified with an independent readback and restored.
- Explicit Power sleep/wake and TV behavior confirmed by the owner.

Controlled live hardening tests passed on the same installation: killing the
relay's main process caused Docker to restart it; stopping private BlueZ made
the decoder stop safely; starting it recreated the decoder; powering the
dedicated adapter off was repaired by its supervisor. The bond-key fingerprint
was unchanged. The owner also confirmed remote control resumed after idle;
some early presses overlapped the maintenance window. These results are
installation-specific, not certification for other hardware.
On 2026-11-14 a controlled hypervisor reboot also returned the guest, both
containers and the bonded remote without manual starts or re-pairing. The
owner confirmed control, then identified a TV/Home-hold panel mismatch in the
original example. Sending native `home` with `hold_secs: 1` instead of the
Companion `control_center` shortcut corrected it; short tap and held-button
behavior were physically confirmed against the original remote. The native
hold adds latency after the receiver's tap/hold threshold. This did not require
changing decoder/runtime images or Bluetooth state. An orderly reboot does
not prove electrical AC-loss recovery.
No full NUC cold reboot, extended idle/soak, every radio/remote generation or
arbitrary HDMI-CEC system is certified by this early release. An automated
button model, HA trace or HTTP status is not physical acceptance.
