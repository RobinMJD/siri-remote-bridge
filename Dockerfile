FROM rust:1-trixie@sha256:0b0ea86881537b3f645aace7e8e39556289f8787db057317c8d4978548213b9e AS build
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    pkg-config libdbus-1-dev libpipewire-0.3-dev libclang-dev libopus-dev \
    && rm -rf /var/lib/apt/lists/*
ADD --checksum=sha256:942ce68ffe631539f4b2d73fec9c1addab73ede63d0bb41e6b4271c7a34a8343 \
    https://codeload.github.com/azais-corentin/siri-remote/tar.gz/3b1d4e0a0fe0317f77368dee9f811e656fe9cb95 /tmp/receiver.tar.gz
WORKDIR /src
RUN tar -xzf /tmp/receiver.tar.gz --strip-components=1 -C /src
RUN cargo build --locked --release -j 2

FROM debian:trixie-slim@sha256:a72b4433de1cf7d6bae0c4cee74d0547f58601a643b3375f070c51600d63b6b2 AS bluez-build
ENV DEBIAN_FRONTEND=noninteractive
RUN printf '%s\n' 'deb-src http://deb.debian.org/debian trixie main' > /etc/apt/sources.list.d/bluez-src.list \
    && apt-get update && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends dpkg-dev quilt \
    && apt-get build-dep -y --no-install-recommends bluez=5.82-1.1 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /src
ADD --checksum=sha256:a452a7352488e55a09eb8d8d8ba883db1bf93df1d06a13b0804bf908fe2099ad \
    https://deb.debian.org/debian/pool/main/b/bluez/bluez_5.82-1.1.dsc /src/
ADD --checksum=sha256:818e2bfa64d3d26b49cc857448f00f4fc7bb76949266de8d7f4c07f8057bf95c \
    https://deb.debian.org/debian/pool/main/b/bluez/bluez_5.82.orig.tar.gz /src/
ADD --checksum=sha256:dd32f06a527859709055912ac8c8a0377030f7f34d7d6a9cc7f5938ed8bac659 \
    https://deb.debian.org/debian/pool/main/b/bluez/bluez_5.82-1.1.debian.tar.xz /src/
RUN dpkg-source -x bluez_5.82-1.1.dsc
COPY patches/bluez-5.82-eir-name-length.patch /src/bluez-5.82/debian/patches/bridge-eir-name-length.patch
COPY scripts/build-bluez-backport.sh /usr/local/bin/build-bluez-backport
RUN /bin/sh /usr/local/bin/build-bluez-backport

FROM debian:trixie-slim@sha256:a72b4433de1cf7d6bae0c4cee74d0547f58601a643b3375f070c51600d63b6b2 AS bluez
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends bluez dbus python3 python3-dbus \
    && rm -rf /var/lib/apt/lists/* \
    && test "$(dpkg-query -W -f='${Version}' bluez)" = '5.82-1.1' \
    && useradd --uid 65532 --no-create-home --shell /usr/sbin/nologin receiver
COPY --from=bluez-build /tmp/bluez-bridge.deb /tmp/bluez-bridge.deb
RUN dpkg -i /tmp/bluez-bridge.deb && rm /tmp/bluez-bridge.deb \
    && test "$(dpkg-query -W -f='${Version}' bluez)" = '5.82-1.1+bridge1'
COPY dbus.conf /etc/siri-remote-dbus.conf
COPY bluez_status.py /opt/siri-remote/bluez_status.py
COPY bluez-entrypoint.sh /usr/local/bin/bluez-entrypoint
ENV DBUS_SYSTEM_BUS_ADDRESS=unix:path=/run/siri-test/system_bus_socket
ENTRYPOINT ["/bin/sh", "/usr/local/bin/bluez-entrypoint"]

FROM debian:trixie-slim@sha256:a72b4433de1cf7d6bae0c4cee74d0547f58601a643b3375f070c51600d63b6b2 AS relay
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    libdbus-1-3 libpipewire-0.3-0 libopus0 python3 python3-dbus \
    && rm -rf /var/lib/apt/lists/*
COPY --from=build /src/target/release/siri-remote /usr/local/bin/siri-remote
COPY relay.py webhook_request.py bluez_status.py healthcheck.py /opt/siri-remote/
USER 65532:65532
ENV DBUS_SYSTEM_BUS_ADDRESS=unix:path=/run/siri-test/system_bus_socket \
    PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
ENTRYPOINT ["python3", "-E", "-s", "/opt/siri-remote/relay.py"]
