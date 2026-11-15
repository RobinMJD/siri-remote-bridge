"""Read private BlueZ state; never return bond keys or remote input data."""

import json
import os
import sys


def probe(address=None):
    import dbus

    bus = dbus.bus.BusConnection(os.environ["DBUS_SYSTEM_BUS_ADDRESS"])
    try:
        objects = dbus.Interface(
            bus.get_object("org.bluez", "/", introspect=False), "org.freedesktop.DBus.ObjectManager"
        ).GetManagedObjects(timeout=2)
        adapters = [
            props["org.bluez.Adapter1"]
            for props in objects.values()
            if "org.bluez.Adapter1" in props
        ]
        devices = [
            props["org.bluez.Device1"]
            for props in objects.values()
            if "org.bluez.Device1" in props
            and str(props["org.bluez.Device1"].get("Address", "")).upper() == address
        ]
        device = devices[0] if devices else {}
        dbus_api = dbus.Interface(
            bus.get_object("org.freedesktop.DBus", "/org/freedesktop/DBus", introspect=False),
            "org.freedesktop.DBus",
        )
        return {
            "available": True,
            "adapter_present": len(adapters) == 1,
            "powered": len(adapters) == 1 and bool(adapters[0].get("Powered", False)),
            "bond_present": bool(device.get("Paired", False) and device.get("Bonded", False)),
            "connected": bool(device.get("Connected", False)),
            "services_resolved": bool(device.get("ServicesResolved", False)),
            "bus_id": str(dbus_api.GetId(timeout=2)),
            "owner": str(dbus_api.GetNameOwner("org.bluez", timeout=2)),
        }
    finally:
        bus.close()


if __name__ == "__main__":
    try:
        status = probe()
    except Exception:
        status = {"available": False, "powered": False}
    if "--health" not in sys.argv:
        print(json.dumps(status))
    sys.exit(0 if status["available"] and status["powered"] else 1)
