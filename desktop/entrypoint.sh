#!/bin/bash
#
# LinuxPilot Desktop Entrypoint
# Starts VNC + noVNC + AT-SPI + LinuxPilot daemon
#

set -e

echo "═══════════════════════════════════════════"
echo "  LinuxPilot Desktop Environment"
echo "═══════════════════════════════════════════"
echo ""

# ── Start VNC server ──
echo "Starting VNC server on :1 (1280x1024)..."
vncserver :1 \
    -geometry 1280x1024 \
    -depth 24 \
    -localhost no \
    2>/dev/null

export DISPLAY=:1

# ── Start AT-SPI accessibility bus ──
echo "Starting AT-SPI bus..."
/usr/libexec/at-spi-bus-launcher --launch-immediately &
sleep 1

# ── Start noVNC ──
echo "Starting noVNC on port 6080..."
websockify \
    --web /usr/share/novnc/ \
    6080 \
    localhost:5901 \
    &>/dev/null &

# ── Generate test data if workspace is empty ──
DOWNLOADS="$HOME/Downloads"
if [ -z "$(ls -A $DOWNLOADS 2>/dev/null)" ]; then
    echo "Generating test dataset in ~/Downloads..."
    python3 -m linuxpilot.testbed.generators w1-downloads "$DOWNLOADS" 2>/dev/null || true
fi

# ── Start LinuxPilot daemon ──
echo "Starting LinuxPilot API on port 8000..."
echo ""
echo "═══════════════════════════════════════════"
echo "  Desktop:   http://localhost:6080"
echo "  API:       http://localhost:8000/api/v1"
echo "  Dashboard: http://localhost:8000/dashboard"
echo "  Docs:      http://localhost:8000/api/v1/openapi.json"
echo ""
echo "  CLI usage:"
echo "    lp doctor        # Check readiness"
echo "    lp run \"goal\"    # Run a task"
echo "    lp diff <id>     # Show changes"
echo "    lp commit <id>   # Commit changes"
echo "═══════════════════════════════════════════"
echo ""

exec lp daemon --host 0.0.0.0 --port 8000
