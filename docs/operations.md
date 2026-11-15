# Operations and recovery

Run all commands from the checked-out release with the same `.env` and Compose
project name. Do not run two BlueZ containers against the same radio/state.

## Health

```sh
docker compose ps
docker compose logs --tail 30 bluez relay
docker compose exec relay cat /run/siri-remote/status.json
```

`phase` is `connected`, `waiting_remote`, `waiting_backend` or
`repair_required`. An asleep/out-of-range remote can be `waiting_remote` with a
healthy relay. Status includes heartbeat, worker liveness, backend/bond status,
reconnect count and aggregate HTTP counts; it includes no webhook or bond keys.
Watch `http_failures` increasing; do not infer physical success from HTTP 200.

Prometheus users may collect this status into their existing node-exporter
textfile collector. Alert on stale heartbeat, stopped components, missing radio
or bond for several minutes; **do not alert on an idle remote alone**. No
public metrics listener or general Docker-socket exporter is needed.

HTTP 200 does not prove HA accepted a command: an automation can silently fail
its conditions. The example permits a sender timestamp up to 250 ms ahead of
HA to tolerate small clock skew between synchronized Linux hosts/VMs, while
still rejecting commands one second old or older. Keep both clocks synchronized;
do not enlarge this margin to hide a broken clock. If buttons arrive but do
nothing, inspect HA automation traces and compare the timestamp condition
before re-pairing or resetting Bluetooth. A real 8 ms negative age reproduced
this failure with the earlier zero-tolerance condition.

## Restart and maintenance

```sh
docker compose restart relay
docker compose restart bluez
# The relay detects a replaced private bus and reacquires it automatically.
docker compose stop
docker compose up -d
```

`unless-stopped` respects a manual stop even after Docker restarts. If the stack
was stopped intentionally, `up -d` is required to re-enable it. Docker's initial
Compose dependency order is not a substitute for runtime readiness/recovery.

If BlueZ has no adapter, inspect USB passthrough, kernel firmware/rfkill and
competing bluetoothd processes first. The private BlueZ supervisor powers its
adapter on, keeps it non-discoverable/non-pairable and restarts itself after a
sustained backend failure. It never resets the host USB bus or removes bonds.

## Pairing repair

If a bond is missing or authentication fails, stop the relay, securely back up
private state, put the **intended spare remote** in pairing mode nearby, and run
the explicit root pairing command in README. Inspect the selected remote before
continuing. Update the identity in private JSON if changed, then recreate the
relay. Do not leave a root pairing container running unattended. Replacing the
Bluetooth adapter or pairing the remote to another Apple TV may require this.

## Backup and restore

1. Stop this stack only for a consistent bond backup.
2. Create an encrypted, root-only backup of `STATE_DIRECTORY/bluetooth`,
   `STATE_DIRECTORY/secrets` and the reviewed source commit/Compose `.env`.
3. Do not restore a stale D-Bus socket or tmpfs status; `bus/` may be recreated.
4. Restart and verify connectivity, then verify backup readability/checksums.

On restoration, use the reviewed source commit, install OS Bluetooth firmware,
attach the adapter and recreate directories/permissions from README. Restore
bonds as root, secret JSON owner 65532:65532 mode 0400 and state root mode 0700.
Restore the HA automation, its secret, Apple TV integration pairing and soundbar
configuration from the independent HA backup. Start BlueZ first, then relay.

Without backups, rebuild source and deliberately pair the remote and Apple TV
again. Generate a new random scoped webhook and update HA secrets accordingly.
Never recover by weakening HA authentication or reusing a secret from a log.

## Upgrade / rollback

For center-button holds, update the HA event allowlist and add the `select_hold`
branch before replacing the relay. It sends `select` with `hold_secs: 1`; the
receiver defers the ordinary click until release and emits a hold only once.
Select uses a 250 ms decision threshold, rather than Back/Home's 650 ms, to
avoid stacking an unnecessary wait before HA's native held-input action.
Clicks released before 250 ms remain ordinary clicks. HA translates
`hold_secs: 1` to its library's Hold action, not a freely tunable duration;
setting it below one sends a normal click on the qualified HA version.
Expect some remaining native-hold/network latency; do not patch HA internals
or send an initial Select click to hide that delay.
Test short clicks, a held thumbnail in YouTube, and navigation afterward. App
menus and supported options are Apple TV/application behavior, not hard-coded
playlist/channel actions in this bridge.

Short Power now emits `power_menu`: the HA example sends `control_center`
when awake or `wakeup` when HA reports sleep/disconnection. Long Power still
emits one explicit `suspend`. The legacy `wakeup` event remains accepted for
rolling upgrade/rollback. Never append `select` to the Power branch: the user
must choose whether to confirm shutdown. This differs from TV/Home hold,
which deliberately uses native held `home` rather than that shortcut.

TV/Home holds emit the compatible `control_center` event, but the HA example
maps it to `remote.send_command` with `command: home` and `hold_secs: 1`.
That preserves native button semantics rather than invoking Companion's
dedicated control-center shortcut (which can focus the power panel). If an
older installation shows the wrong panel, back up its automation, add this
branch from the example, run HA's configuration check and reload Automations.
Do not change Bluetooth pairing, Power handling, or decoder thresholds. Verify
short tap and hold against the original remote on the same tvOS screen;
different Apple TV versions can present different panels. Roll back just the
automation preimage if needed. An HTTP success alone is not physical acceptance.

Keep a working source tag, both image IDs and a **cold private-state backup**.
Review the diff, run CI/static checks and build the candidate images before
stopping the old stack. Tag working images locally for rollback; do not prune
them during maintenance. Recreate only this stack and verify a real navigation,
hold, mute and sleep/wake cycle plus disconnect recovery.

On failure, stop the candidate, preserve its state/evidence, restore exact
prechange Compose/source/image IDs and restore cold state only if needed.
Never overwrite newer private state blindly or reset another service to get a
clean checkout. Dependency PRs are reviewed; upstream movement is not a reason
to replace a tested decoder automatically.

## Qualification tests

Run unit tests and image tests from CONTRIBUTING. On real hardware also test:
relay crash, BlueZ/D-Bus restart, a forced disconnect, backend powered off/on,
late adapter availability, remote idle then wake, and a full host/VM reboot in
an approved maintenance window. After each, ensure subscriptions return, no
old input replays, bonds remain intact and actual buttons still control HA.
Avoid issuing disruptive Power/mute tests without the occupant's approval.
