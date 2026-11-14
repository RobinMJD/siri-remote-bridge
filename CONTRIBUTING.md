# Contributing

Please open an issue describing hardware, OS, BlueZ/firmware versions and a
reproduction before a large change. Redact IPs, webhook IDs, Bluetooth identity
addresses and all bond material. Never attach an entire private state directory.

Run `python3 -B -m unittest discover -s tests -v`, `ruff check .`,
`ruff format --check .`, `sh -n bluez-entrypoint.sh` and
`docker compose config -q`. Build both images and repeat tests in the relay
image. Test hardware is required for claims about pairing, reconnect, key
semantics, HDMI-CEC and radio range; CI alone cannot certify those.

Keep the upstream decoder pinned with checksum and Cargo.lock. Prefer changes
upstream rather than an undocumented local fork. Add regression tests for
input expiry, disconnect cleanup, unsafe pairing and accidental repeats.
Avoid retrying commands whose first delivery is ambiguous. Do not add broad
HA tokens, public listeners, Docker socket mounts or silent auto-pairing.

Pull requests must describe impact, tests, known gaps and a rollback. Do not
promise every Siri Remote generation or Bluetooth chipset without physical
evidence. License contributions under GPL-3.0-or-later.
