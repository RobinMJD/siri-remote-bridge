#!/bin/sh
set -eu

cd /src/bluez-5.82
printf '%s\n' bridge-eir-name-length.patch >> debian/patches/series
{
    printf 'bluez (5.82-1.1+bridge1) trixie; urgency=medium\n\n  * Backport the upstream EIR device-name length fix (CVE-2026-80186).\n\n -- Siri Remote Bridge <maintainers@invalid.example>  Sun, 15 Nov 2026 00:00:00 +0000\n\n'
    cat debian/changelog
} > /tmp/bluez-changelog
mv /tmp/bluez-changelog debian/changelog

QUILT_PATCHES=debian/patches quilt push
grep -q 'len = MIN(len, HCI_MAX_NAME_LENGTH)' src/eir.c

if ! dpkg-buildpackage -B -us -uc -j2 > /tmp/bluez-build.log 2>&1; then
    tail -n 120 /tmp/bluez-build.log >&2
    exit 1
fi
if ! make unit/test-eir > /tmp/bluez-unit-build.log 2>&1; then
    tail -n 120 /tmp/bluez-unit-build.log >&2
    exit 1
fi
if ! unit/test-eir > /tmp/bluez-unit-test.log 2>&1; then
    tail -n 120 /tmp/bluez-unit-test.log >&2
    exit 1
fi

cp "../bluez_5.82-1.1+bridge1_$(dpkg --print-architecture).deb" /tmp/bluez-bridge.deb
test "$(dpkg-deb -f /tmp/bluez-bridge.deb Version)" = '5.82-1.1+bridge1'
