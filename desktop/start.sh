#!/bin/bash
set -e

echo "Starting LinuxPilot Agent Desktop..."

# Start D-Bus
service dbus start || true

# Start AT-SPI bus
/usr/libexec/at-spi-bus-launcher --launch-immediately &

# Start Xvnc
Xvnc :1 -geometry 1920x1080 -depth 24 &
export DISPLAY=:1

# Start XFCE
startxfce4 &

# Start noVNC
cd /usr/share/novnc
./utils/novnc_proxy --vnc localhost:5901 --listen 6080 &

echo "Agent desktop ready."
echo "Access via noVNC at http://localhost:6080"
echo "VNC at localhost:5901"

# Keep container running
tail -f /dev/null
