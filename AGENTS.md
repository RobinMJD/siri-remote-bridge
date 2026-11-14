# Maintainer / coding-agent instructions

- Read README, docs/security.md and docs/operations.md before changes.
- Keep this repository generic. No deployment addresses, user names, real
  webhook IDs, Bluetooth identities, pairing PINs or private state in Git.
- This is a library/receiver project, not authorization to deploy to a user's
  home, re-pair remotes, toggle power/audio or restart a hypervisor.
- Keep the private D-Bus boundary, fixed configured destination, expiring input,
  no ambiguous retries and rootless decoder. Never remove a bond automatically.
- Use the pinned upstream decoder with Cargo.lock/checksum. Any protocol patch
  needs separate review, tests, attribution and an explicit upgrade recipe.
- Add regression tests; run unit tests, lint/format, shell syntax, Compose
  validation, container entrypoint smoke and image tests. For hardware changes,
  record physical results separately from CI/config/HTTP success.
- Prefer small reversible changes. Preserve working images and encrypted
  private-state backups. Never overwrite dirty unrelated deployment sources.
- Update CHANGELOG and the relevant docs with limitations and rollback.
