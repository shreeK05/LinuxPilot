#!/usr/bin/env bash
#
# LinuxPilot One-Shot Ubuntu Installer
# Installs everything needed to run LinuxPilot on Ubuntu 24.04 LTS
#
# Usage: curl -sL https://linuxpilot.dev/install.sh | bash
#   OR:  ./install.sh
#

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}"
echo "╔══════════════════════════════════════════╗"
echo "║       LinuxPilot Installer v1.0          ║"
echo "║  Trust-First OS Agent for Linux          ║"
echo "╚══════════════════════════════════════════╝"
echo -e "${NC}"

# ── Pre-checks ─────────────────────────────────────────────

# Must be Linux
if [ "$(uname -s)" != "Linux" ]; then
    echo -e "${RED}✗ LinuxPilot requires Linux. You are running $(uname -s).${NC}"
    exit 1
fi

# Must be Ubuntu
if [ ! -f /etc/os-release ]; then
    echo -e "${RED}✗ Cannot detect OS version.${NC}"
    exit 1
fi

source /etc/os-release
if [ "$ID" != "ubuntu" ]; then
    echo -e "${YELLOW}⚠ LinuxPilot is designed for Ubuntu 24.04. You are running ${PRETTY_NAME}.${NC}"
    echo -e "${YELLOW}  Continuing, but some features may not work.${NC}"
fi

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
if [ "$(echo "$PYTHON_VERSION >= 3.12" | bc 2>/dev/null || echo 0)" != "1" ]; then
    echo -e "${YELLOW}⚠ Python $PYTHON_VERSION detected. Python ≥3.12 recommended.${NC}"
fi

echo -e "${GREEN}Installing system dependencies...${NC}"

sudo apt-get update -qq
sudo apt-get install -y -qq \
    python3.12-venv python3-dev build-essential \
    python3-gi gir1.2-atspi-2.0 at-spi2-core \
    python3-seccomp libseccomp-dev \
    dbus-x11 xdotool \
    strace cgroup-tools \
    curl git \
    2>/dev/null

echo -e "${GREEN}✓ System dependencies installed${NC}"

# ── Clone or update ────────────────────────────────────────

INSTALL_DIR="${HOME}/LinuxPilot"

if [ -d "$INSTALL_DIR/.git" ]; then
    echo -e "${GREEN}Updating existing installation...${NC}"
    cd "$INSTALL_DIR"
    git pull --ff-only 2>/dev/null || true
else
    echo -e "${GREEN}Cloning LinuxPilot...${NC}"
    if [ -d "$INSTALL_DIR" ]; then
        # Directory exists but is not a git repo — back it up
        mv "$INSTALL_DIR" "${INSTALL_DIR}.bak.$(date +%s)"
    fi
    git clone https://github.com/linuxpilot/linuxpilot.git "$INSTALL_DIR" 2>/dev/null || {
        # If git clone fails (e.g., no network), check if we're running from the repo
        if [ -f "pyproject.toml" ] && grep -q "linuxpilot" "pyproject.toml" 2>/dev/null; then
            INSTALL_DIR="$(pwd)"
            echo -e "${YELLOW}Using local directory: $INSTALL_DIR${NC}"
        else
            echo -e "${RED}✗ Failed to clone repository.${NC}"
            exit 1
        fi
    }
fi

cd "$INSTALL_DIR"

# ── Python environment ─────────────────────────────────────

echo -e "${GREEN}Setting up Python environment...${NC}"

python3 -m venv --system-site-packages .venv
source .venv/bin/activate

pip install --upgrade pip -q
pip install -e ".[dev]" -q 2>/dev/null || pip install -e . -q

echo -e "${GREEN}✓ Python environment ready${NC}"

# ── System configuration ──────────────────────────────────

echo -e "${GREEN}Configuring system...${NC}"

# Relax AppArmor for unprivileged user namespaces (Ubuntu 24.04)
echo 'kernel.apparmor_restrict_unprivileged_userns=0' | sudo tee /etc/sysctl.d/60-lp.conf >/dev/null 2>&1
sudo sysctl --system >/dev/null 2>&1

# Create workspace directory
sudo mkdir -p /var/lib/linuxpilot
sudo chown "$USER:$USER" /var/lib/linuxpilot

# Create audit and cassette directories
mkdir -p audit cassettes

# Accessibility environment
cat <<'EOF' | sudo tee /etc/profile.d/linuxpilot-accessibility.sh >/dev/null
export GTK_MODULES=gail:atk-bridge
export QT_LINUX_ACCESSIBILITY_ALWAYS_ON=1
export ACCESSIBILITY_ENABLED=1
export GNOME_ACCESSIBILITY=1
EOF

echo -e "${GREEN}✓ System configured${NC}"

# ── Environment file ─────────────────────────────────────

if [ ! -f .env ]; then
    cp .env.example .env 2>/dev/null || true
    echo -e "${YELLOW}⚠ Created .env file. Edit it to add your LLM API keys.${NC}"
fi

# ── Run doctor ─────────────────────────────────────────────

echo ""
echo -e "${CYAN}Running system diagnostics...${NC}"
echo ""
source .venv/bin/activate
lp doctor || true

echo ""
echo -e "${GREEN}═══════════════════════════════════════════${NC}"
echo -e "${GREEN}  Installation complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════${NC}"
echo ""
echo -e "  ${CYAN}Quick Start:${NC}"
echo -e "    cd $INSTALL_DIR"
echo -e "    source .venv/bin/activate"
echo -e ""
echo -e "  ${CYAN}Start the daemon:${NC}"
echo -e "    lp daemon"
echo -e ""
echo -e "  ${CYAN}In another terminal:${NC}"
echo -e "    lp run \"Organize my Downloads by file type\""
echo -e ""
echo -e "  ${CYAN}Or run with Docker:${NC}"
echo -e "    docker build -t linuxpilot-desktop ."
echo -e "    docker run --cap-add SYS_ADMIN -p 6080:6080 -p 8000:8000 linuxpilot-desktop"
echo -e "    # Open http://localhost:6080 for the desktop"
echo ""
