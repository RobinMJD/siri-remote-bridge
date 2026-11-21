# Changelog

## Unreleased

- Extend directional button repeats from 3 to 20 seconds for tasks like
  scrubbing in YouTube. The relay stops generating repeats on release or disconnect.

- Require an explicit webhook transport choice for new installs and a trusted-LAN
  acknowledgement for HTTP. Existing explicit HTTP configurations still load.
- Bound the entire webhook request with a disposable process so a slow response
  cannot stall the sole sender; preserve command expiry and no retries.
- Replace the receiver's broad BlueZ D-Bus permission with named methods needed
  by the pinned decoder; pairing and bond removal remain root-only.
- Upgrade Debian packages during image builds so security fixes newer than the
  pinned base-image digests are included.

- Link the complete Compose project and environment template directly from the
  setup guide, with a configuration check before building the containers.

- Lead the README with the simultaneous two-remotes use case and a scalable
  diagram of the Bluetooth and local-network paths.

- Lower only Select's hold decision threshold from 650 to 250 ms after physical
  feedback about added latency. Back/Home/Power thresholds are unchanged; a
  249 ms click remains a click and holding never sends an initial tap.

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
