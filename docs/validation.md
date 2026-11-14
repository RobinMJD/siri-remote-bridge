# Validation scope

Initial software suite: 47 unit/contract tests covering button mapping and hold
thresholds, bounded repeats, fresh/stale reports, disconnect queue generations,
backend replacement, missing bonds, manual authentication recovery, worker
liveness, timeout/no-retry behavior, TLS validation and container policies.
CI repeats on Python 3.11, 3.13 and 3.14 and builds/runs the Linux image tests.

Pre-hardening physical prototype on the hardware described in hardware.md:

- Navigation and selection confirmed by the owner.
- Home hold opens Control Centre; Back hold returns Home without an initial
  Back tap; both confirmed by the owner.
- Direct soundbar mute verified with an independent readback and restored.
- Explicit Power sleep/wake and TV behavior confirmed by the owner.

Boot/reconnect hardening is being qualified separately. The maintainer records
controlled restart/disconnect results in release notes only after actual runs.
No full NUC cold reboot, extended idle/soak, every radio/remote generation or
arbitrary HDMI-CEC system is certified by this early release. An automated
button model, HA trace or HTTP status is not physical acceptance.
