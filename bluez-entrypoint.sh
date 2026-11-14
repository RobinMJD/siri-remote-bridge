#!/bin/sh
set -eu
export DBUS_SYSTEM_BUS_ADDRESS=unix:path=/run/siri-test/system_bus_socket
bus_pid=''
bluez_pid=''
cleanup() {
    trap - EXIT INT TERM
    [ -z "$bluez_pid" ] || kill "$bluez_pid" 2>/dev/null || true
    [ -z "$bus_pid" ] || kill "$bus_pid" 2>/dev/null || true
    wait 2>/dev/null || true
}
trap cleanup EXIT
trap 'exit 0' INT TERM
rm -f /run/siri-test/system_bus_socket
dbus-daemon --config-file=/etc/siri-remote-dbus.conf --nofork &
bus_pid=$!
for attempt in 1 2 3 4 5; do
    if dbus-send --system --print-reply --dest=org.freedesktop.DBus \
        /org/freedesktop/DBus org.freedesktop.DBus.ListNames >/dev/null 2>&1; then
        break
    fi
    sleep 1
done
test -S /run/siri-test/system_bus_socket
/usr/libexec/bluetooth/bluetoothd --nodetach \
    --noplugin=input,hog,a2dp,avrcp,sap,network,health,neard,sixaxis,autopair,hostname &
bluez_pid=$!
failures=0
while kill -0 "$bus_pid" 2>/dev/null && kill -0 "$bluez_pid" 2>/dev/null; do
    # Only this passed-through adapter is visible on this private bus.
    bluetoothctl --timeout 3 power on >/dev/null 2>&1 || true
    bluetoothctl --timeout 3 pairable off >/dev/null 2>&1 || true
    bluetoothctl --timeout 3 discoverable off >/dev/null 2>&1 || true
    if python3 /opt/siri-remote/bluez_status.py --health; then
        failures=0
    else
        failures=$((failures + 1))
        if [ "$failures" -ge 12 ]; then
            printf '%s\n' 'BLUEZ_UNAVAILABLE restarting private stack component' >&2
            exit 1
        fi
    fi
    sleep 5
done
exit 1
