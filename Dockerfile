FROM rust:1-trixie@sha256:0b0ea86881537b3f645aace7e8e39556289f8787db057317c8d4978548213b9e AS build
RUN apt-get update && apt-get install -y --no-install-recommends \
    pkg-config libdbus-1-dev libpipewire-0.3-dev libclang-dev libopus-dev \
    && rm -rf /var/lib/apt/lists/*
ADD --checksum=sha256:942ce68ffe631539f4b2d73fec9c1addab73ede63d0bb41e6b4271c7a34a8343 \
    https://codeload.github.com/azais-corentin/siri-remote/tar.gz/3b1d4e0a0fe0317f77368dee9f811e656fe9cb95 /tmp/receiver.tar.gz
WORKDIR /src
RUN tar -xzf /tmp/receiver.tar.gz --strip-components=1 -C /src
RUN cargo build --locked --release -j 2

FROM debian:trixie-slim@sha256:a72b4433de1cf7d6bae0c4cee74d0547f58601a643b3375f070c51600d63b6b2 AS bluez
RUN apt-get update && apt-get install -y --no-install-recommends bluez dbus python3 python3-dbus \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --uid 65532 --no-create-home --shell /usr/sbin/nologin receiver
COPY dbus.conf /etc/siri-remote-dbus.conf
COPY bluez_status.py /opt/siri-remote/bluez_status.py
COPY bluez-entrypoint.sh /usr/local/bin/bluez-entrypoint
ENV DBUS_SYSTEM_BUS_ADDRESS=unix:path=/run/siri-test/system_bus_socket
ENTRYPOINT ["/bin/sh", "/usr/local/bin/bluez-entrypoint"]

FROM debian:trixie-slim@sha256:a72b4433de1cf7d6bae0c4cee74d0547f58601a643b3375f070c51600d63b6b2 AS relay
RUN apt-get update && apt-get install -y --no-install-recommends \
    libdbus-1-3 libpipewire-0.3-0 libopus0 python3 python3-dbus \
    && rm -rf /var/lib/apt/lists/*
COPY --from=build /src/target/release/siri-remote /usr/local/bin/siri-remote
COPY relay.py bluez_status.py healthcheck.py /opt/siri-remote/
USER 65532:65532
ENV DBUS_SYSTEM_BUS_ADDRESS=unix:path=/run/siri-test/system_bus_socket \
    PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
ENTRYPOINT ["python3", "-E", "-s", "/opt/siri-remote/relay.py"]
