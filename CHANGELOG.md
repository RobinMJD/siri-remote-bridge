# Changelog

## Unreleased

- Send a native held Home command for TV/Home holds in the HA example. The
  Companion `control_center` shortcut can instead open the power-focused panel
  on some tvOS versions. The wire event name stays compatible; decoder, images,
  short taps, and Power handling are unchanged. Reload HA Automations after
  updating the example; no receiver image rebuild is needed for this fix.

## 0.1.0 - 2026-11-14

- Initial Linux/BlueZ container bridge using a pinned upstream HID decoder.
- Expiring, scoped Home Assistant webhook commands with fixed-target examples.
- Independent Back/Home/Power hold handling and bounded navigation repeats.
- Persistent bonding, manual pairing, Docker boot recovery and backend recovery.
- Liveness status that does not treat an idle or sleeping remote as a fault.
- Tests, pinned CI actions, deployment, security, recovery and hardware runbooks.
- Clear deferred input immediately when decoder output closes, not on the next poll.
- Verified controlled live crash/backend/power recovery without replacing the bond.
