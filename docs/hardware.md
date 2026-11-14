# Hardware compatibility

| Layer | Evidence / requirement |
| --- | --- |
| Receiver OS | Tested on Debian 13, Linux 6.12, Docker Engine/Compose |
| Host | Tested with Intel Bluetooth USB ID 8087:0037 passed into an existing x86-64 VM |
| Remote | One physical USB-C Siri Remote, Bluetooth PnP vendor 004C/product 0316; owner described it as generation 4, not independently SKU-verified |
| Decoder | Upstream documents generation-3 experimental support; pinned commit listed in THIRD_PARTY.md |
| Other Linux PCs / USB dongles | Architecturally supported when BlueZ exposes the same adapter/GATT APIs; physical qualification required |
| Raspberry Pi / ARM64 | Intended portable build, not physically qualified; verify board firmware and Cargo native dependencies |
| macOS / Docker Desktop | Not supported as the Linux Bluetooth receiver; Docker Desktop does not expose host Bluetooth as BlueZ |
| Multiple adapters | Deliberately refused by readiness probe; isolate exactly one adapter rather than selecting an arbitrary radio |
| Arbitrary non-Apple remotes | Not supported by this input decoder |

Proxmox USB passthrough is optional. Inspect VM hardware first, ensure the adapter
is not used by the host or another VM, then attach it persistently through the
normal hypervisor interface. Do not overwrite an occupied USB slot blindly.
Enable VM autostart and Docker startup independently; containers cannot start a
stopped VM or power on a host whose BIOS does not recover after AC loss.

Install matching vendor Bluetooth firmware inside the guest through your OS
package manager. USB passthrough alone does not provide guest firmware. USB IDs
can change with replacement hardware, so recheck passthrough after replacement.

Pair close to the adapter. The pinned decoder's pairing candidate selection
requires roughly RSSI >= -55 dBm; weak signal was enough to block initial pairing
in the tested setup. RF range inside furniture and with different antennas is
not guaranteed. Try a USB extension/antenna placement before changing software.
