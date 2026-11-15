# Changelog

## Unreleased

- Add center Select hold: defer a normal click until release and send one native
  held-Select event, without opening/playing the item first. Requires the matching
  HA `select_hold` allowlist and command branch; no decoder or pairing change.
- Short Power opens the native power-focused menu when awake, or wakes when
  asleep; long Power still sleeps once. Never auto-confirm shutdown. Keep the
  old `wakeup` event supported for rolling rollback.

- Permit bounded 250 ms cross-host clock skew in the HA freshness condition;
  preserve the one-second expiry for old input. A synchronized VM only 8 ms
  behind the sender otherwise silently dropped every button despite HTTP 200.

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
