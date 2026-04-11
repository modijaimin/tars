#!/bin/bash
set -e

# Copy personal.md from persistent volume into context dir
if [ -f /data/personal.md ]; then
  cp /data/personal.md /app/context/personal.md
  echo "Copied /data/personal.md to /app/context/personal.md"
else
  echo "WARNING: /data/personal.md not found — context/personal.md will be empty"
  touch /app/context/personal.md
fi

# Start Tailscale in userspace mode
tailscaled --tun=userspace-networking --socks5-server=localhost:1055 &
sleep 2
tailscale up --authkey="${TS_AUTHKEY}" --hostname=personal-tars --accept-routes

# Hand off to supervisord
exec supervisord -c /app/supervisord.conf
