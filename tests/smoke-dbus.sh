#!/bin/sh
# Exercise the receiver policy against a real private bus and a named peer.
set -eu
dbus-daemon --config-file=/etc/siri-remote-dbus.conf --fork
python3 - <<'PY' &
import dbus
import time

bus = dbus.bus.BusConnection('unix:path=/run/siri-test/system_bus_socket')
bus.request_name('org.bluez')
time.sleep(5)
PY
peer=$!
trap 'kill "$peer" 2>/dev/null || true' EXIT INT TERM
sleep 1

allowed=$(su -s /bin/sh receiver -c \
    'dbus-send --system --print-reply --reply-timeout=500 --dest=org.bluez / org.freedesktop.DBus.ObjectManager.GetManagedObjects' 2>&1 || true)
case "$allowed" in
    *UnknownMethod*|*NoReply*) ;;
    *) printf 'ObjectManager was not allowed: %s\n' "$allowed" >&2; exit 1 ;;
esac

for forbidden in \
    'org.freedesktop.DBus.Properties.Set string:org.bluez.Adapter1 string:Pairable variant:boolean:true' \
    'org.bluez.Device1.Pair' \
    'org.bluez.Adapter1.RemoveDevice'; do
    denied=$(su -s /bin/sh receiver -c \
        "dbus-send --system --print-reply --reply-timeout=500 --dest=org.bluez / $forbidden" 2>&1 || true)
    case "$denied" in
        *AccessDenied*) ;;
        *) printf 'Unexpected BlueZ permission for %s: %s\n' "$forbidden" "$denied" >&2; exit 1 ;;
    esac
done
