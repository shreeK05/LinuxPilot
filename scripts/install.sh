#!/usr/bin/env bash
#
# LinuxPilot Installation Script
# One-click installation for LinuxPilot
#

set -euo pipefail

echo "=========================================="
echo "LinuxPilot Installation"
echo "=========================================="

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    VERSION=$VERSION_ID
else
    echo "Cannot detect OS. This script requires Ubuntu 24.04 LTS."
    exit 1
fi

if [ "$OS" != "ubuntu" ]; then
    echo "This script is designed for Ubuntu. You may need to adapt it for $OS."
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "Please do not run this script as root. Use sudo only when needed."
    exit 1
fi

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
    git \
    pkg-config

# Install Python dependencies
echo "Setting up Python environment..."
cd "$(dirname "$0")/.."

# Create venv with system site-packages (required for python3-gi and python3-seccomp)
python3 -m venv --system-site-packages .venv
source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel

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
    echo "LinuxPilot requires cgroup v2. Please check your kernel configuration."
    exit 1
fi

# Enable accessibility
echo "Configuring accessibility..."
sudo mkdir -p /etc/profile.d
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

# Create audit and cassette directories
mkdir -p audit cassettes

# Configure environment
echo "Configuring environment..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env from template"
    echo "Please edit .env with your LLM API keys (optional)"
fi

# Run doctor to verify setup
echo ""
echo "Running system doctor..."
source .venv/bin/activate
if lp doctor; then
    echo ""
    echo "=========================================="
    echo "Installation complete!"
    echo "=========================================="
    echo ""
    echo "Next steps:"
    echo "1. Edit .env with your LLM API keys (optional)"
    echo "2. Start the daemon: lp daemon"
    echo "3. In another terminal, run: lp run \"your goal\""
    echo ""
    echo "For GUI automation, you may need to start the AT-SPI bus:"
    echo "  /usr/libexec/at-spi-bus-launcher --launch-immediately &"
    echo ""
    echo "To access the web dashboard, navigate to http://localhost:5173"
    echo "after starting the daemon."
else
    echo ""
    echo "Installation completed but some checks failed."
    echo "Please fix the issues reported by 'lp doctor' before using LinuxPilot."
    exit 1
fi
