#!/bin/sh
# Prove the real entrypoint remains alive with no D-Bus, radio or HA endpoint.
set -eu
tmp=$(mktemp -d)
container=''
cleanup() {
    [ -z "$container" ] || docker rm -f "$container" >/dev/null 2>&1 || true
    rm -rf "$tmp"
}
trap cleanup EXIT INT TERM
python3 - "$tmp/config.json" <<'PY'
import json,os,sys
with open(sys.argv[1], 'w') as handle:
    json.dump({'host':'192.0.2.10','port':8123,'webhook_id':'0'*64,
               'address':'00:11:22:33:44:55'},handle)
os.chmod(sys.argv[1],0o444)
PY
container=$(docker run -d --network none --read-only --cap-drop ALL \
    --tmpfs /run/siri-remote:uid=65532,gid=65532,mode=0700 \
    -v "$tmp/config.json:/run/secrets/ha_webhook.json:ro" \
    local/siri-remote-bridge-relay:0.1.0)
sleep 5
docker exec "$container" python3 /opt/siri-remote/healthcheck.py
docker exec "$container" cat /run/siri-remote/status.json
