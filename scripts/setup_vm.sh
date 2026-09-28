#!/usr/bin/env bash
#
# LinuxPilot VM Setup Script
# One-shot setup for Ubuntu 24.04 LTS
#

set -euo pipefail

echo "=========================================="
echo "LinuxPilot VM Setup"
echo "=========================================="

# Update system
echo "Updating system packages..."
sudo apt update
sudo apt upgrade -y

# Install system dependencies
echo "Installing system dependencies..."
sudo apt install -y \
    python3.12-venv \
    python3-dev \
    build-essential \
    python3-gi \
    gir1.2-atspi-2.0 \
    at-spi2-core \
    accerciser \
    python3-seccomp \
    libseccomp-dev \
    xfce4 \
    xfce4-terminal \
    thunar \
    dbus-x11 \
    xdotool \
    tigervnc-standalone-server \
    novnc \
    websockify \
    libreoffice-calc \
    firefox \
    tesseract-ocr \
    strace \
    cgroup-tools \
    curl \
    git

# Install Python dependencies
echo "Setting up Python environment..."
cd /home/$USER/LinuxPilot

# Create venv with system site-packages (required for python3-gi and python3-seccomp)
python3 -m venv --system-site-packages .venv
source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install LinuxPilot in development mode
pip install -e ".[dev]"

# Relax AppArmor restriction for unprivileged user namespaces (Ubuntu 24.04)
echo "Configuring unprivileged user namespaces..."
echo 'kernel.apparmor_restrict_unprivileged_userns=0' | sudo tee /etc/sysctl.d/60-lp.conf
sudo sysctl --system

# Verify cgroup v2
echo "Verifying cgroup v2..."
if [ -f /sys/fs/cgroup/cgroup.controllers ]; then
    echo "✓ cgroup v2 is available"
else
    echo "✗ cgroup v2 is not available"
    exit 1
fi

# Enable accessibility
echo "Configuring accessibility..."
cat << 'EOF' | sudo tee /etc/profile.d/linuxpilot-accessibility.sh
export GTK_MODULES=gail:atk-bridge
export QT_LINUX_ACCESSIBILITY_ALWAYS_ON=1
export ACCESSIBILITY_ENABLED=1
export GNOME_ACCESSIBILITY=1
EOF

# Create workspace directory
echo "Creating workspace directory..."
sudo mkdir -p /var/lib/linuxpilot
sudo chown $USER:$USER /var/lib/linuxpilot

# Create audit directory
mkdir -p audit
mkdir -p cassettes

# Configure environment
echo "Configuring environment..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Please edit .env with your API keys"
fi

# Run doctor to verify setup
echo "Running system doctor..."
source .venv/bin/activate
lp doctor

echo ""
echo "=========================================="
echo "Setup complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Edit .env with your LLM API keys (optional)"
echo "2. Start the daemon: lp daemon"
echo "3. In another terminal, run: lp run \"your goal\""
echo ""
echo "For GUI automation, you may need to start the AT-SPI bus:"
echo "  /usr/libexec/at-spi-bus-launcher --launch-immediately &"
