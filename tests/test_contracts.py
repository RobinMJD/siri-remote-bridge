"""Deployment contracts that must hold even without Bluetooth hardware in CI."""

import pathlib
import re
import unittest
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[1]


class Contracts(unittest.TestCase):
    def test_receiver_bluez_methods_are_allowlisted(self):
        tree = ET.parse(ROOT / "dbus.conf")
        receiver = tree.find("policy[@user='receiver']")
        allowed = {
            (x.get("send_interface"), x.get("send_member")) for x in receiver.findall("allow")
        }
        self.assertIn(("org.bluez.Device1", "Connect"), allowed)
        self.assertIn(("org.bluez.GattCharacteristic1", "StartNotify"), allowed)
        self.assertIn(("org.freedesktop.DBus.ObjectManager", "GetManagedObjects"), allowed)
        self.assertNotIn(("org.freedesktop.DBus.Properties", "Set"), allowed)
        self.assertNotIn(("org.bluez.Adapter1", "StartDiscovery"), allowed)
        self.assertNotIn(("org.bluez.Device1", "Pair"), allowed)
        self.assertNotIn(("org.bluez.Adapter1", "RemoveDevice"), allowed)
        for rule in receiver.findall("allow"):
            self.assertEqual(rule.get("send_destination"), "org.bluez")
            self.assertEqual(rule.get("send_type"), "method_call")
            self.assertIsNotNone(rule.get("send_interface"))
            self.assertIsNotNone(rule.get("send_member"))

    def test_build_pins_decoder_checksum_and_lockfile(self):
        source = (ROOT / "Dockerfile").read_text()
        self.assertIn("--checksum=sha256:", source)
        self.assertIn("cargo build --locked", source)
        bases = re.findall(r"^FROM\s+(\S+)", source, re.MULTILINE)
        self.assertTrue(bases)
        self.assertTrue(all("@sha256:" in base for base in bases))

    def test_compose_is_unattended_but_not_privileged(self):
        source = (ROOT / "compose.yaml").read_text()
        self.assertEqual(source.count("restart: unless-stopped"), 2)
        self.assertNotIn("privileged:", source)
        self.assertNotIn("docker.sock", source)
        self.assertNotIn("ports:", source)
        self.assertEqual(source.count("healthcheck:"), 2)
        self.assertIn('tmpfs: ["/tmp:size=8m,mode=1777"]', source)


if __name__ == "__main__":
    unittest.main()
