# Third-party software

The Bluetooth/HID decoder is built without source modifications from
[azais-corentin/siri-remote](https://github.com/azais-corentin/siri-remote),
commit `3b1d4e0a0fe0317f77368dee9f811e656fe9cb95` (GPL-3.0).
Its source archive SHA-256 is
`942ce68ffe631539f4b2d73fec9c1addab73ede63d0bb41e6b4271c7a34a8343`.
The Dockerfile verifies that archive and uses its Cargo.lock via `--locked`.
Decoder source remains available at that immutable commit and in the build
stage. Preserve its copyright notices and supply corresponding source and
license obligations when redistributing images; see LICENSE.

The Python bridge, Compose configuration, tests and documentation are local
additions licensed GPL-3.0-or-later. They are not an Apple, Home Assistant,
BlueZ or upstream decoder project, endorsement or warranty.

Images include Debian packages, BlueZ, D-Bus and the Rust dependency tree;
their respective licenses still apply. No binary firmware or pairing data is
distributed here. Install firmware through your operating system vendor.
