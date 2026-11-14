"""Deployment contracts that must hold even without Bluetooth hardware in CI."""

import pathlib
import unittest
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[1]


class Contracts(unittest.TestCase):
    def test_receiver_cannot_pair_or_remove_bonds(self):
        tree = ET.parse(ROOT / "dbus.conf")
        receiver = tree.find("policy[@user='receiver']")
        denied = {x.get("send_member") for x in receiver.findall("deny")}
        self.assertEqual(denied, {"Pair", "RemoveDevice"})

    def test_build_pins_decoder_checksum_and_lockfile(self):
        source = (ROOT / "Dockerfile").read_text()
        self.assertIn("--checksum=sha256:", source)
        self.assertIn("cargo build --locked", source)
        self.assertEqual(source.count("@sha256:"), 3)

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
