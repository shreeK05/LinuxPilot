########################################################################
# LinuxPilot Desktop Dockerfile
# Ubuntu 24.04 LTS with XFCE, VNC, noVNC, AT-SPI, and LinuxPilot
# Build:  docker build -t linuxpilot-desktop .
# Run:    docker run --cap-add SYS_ADMIN --cap-add SYS_PTRACE \
#              --security-opt apparmor=unconfined \
#              -p 6080:6080 -p 8000:8000 linuxpilot-desktop
# Access: http://localhost:6080    (noVNC desktop)
#          http://localhost:8000    (LinuxPilot API + dashboard)
########################################################################

FROM ubuntu:24.04

LABEL maintainer="LinuxPilot Team"
LABEL description="LinuxPilot Desktop — Trust-First OS Agent with ACID semantics"

ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

# ── System packages ──────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Python
    python3.12 python3.12-venv python3-dev python3-pip \
    python3-gi gir1.2-atspi-2.0 python3-seccomp libseccomp-dev \
    # Desktop environment
    xfce4 xfce4-terminal thunar mousepad \
    # VNC + noVNC
    tigervnc-standalone-server tigervnc-common \
    novnc websockify \
    # Accessibility
    at-spi2-core dbus-x11 \
    # GUI automation
    xdotool \
    # Applications for demo workflows
    libreoffice-calc firefox \
    # System tools
    strace cgroup-tools curl git \
    build-essential procps nano \
    # Fonts
    fonts-liberation fonts-noto \
    # Clean up
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ── Create user ──────────────────────────────────────────────
RUN useradd -m -s /bin/bash pilot \
    && echo "pilot:pilot" | chpasswd \
    && usermod -aG sudo pilot

# ── Accessibility env ────────────────────────────────────────
RUN cat <<'EOF' > /etc/profile.d/accessibility.sh
export GTK_MODULES=gail:atk-bridge
export QT_LINUX_ACCESSIBILITY_ALWAYS_ON=1
export ACCESSIBILITY_ENABLED=1
export GNOME_ACCESSIBILITY=1
EOF

# ── VNC configuration ────────────────────────────────────────
RUN mkdir -p /home/pilot/.vnc \
    && echo "pilot" | vncpasswd -f > /home/pilot/.vnc/passwd \
    && chmod 600 /home/pilot/.vnc/passwd

RUN cat <<'EOF' > /home/pilot/.vnc/xstartup
#!/bin/bash
unset SESSION_MANAGER
unset DBUS_SESSION_BUS_ADDRESS
export GTK_MODULES=gail:atk-bridge
export QT_LINUX_ACCESSIBILITY_ALWAYS_ON=1
export ACCESSIBILITY_ENABLED=1
/usr/libexec/at-spi-bus-launcher --launch-immediately &
dbus-launch --exit-with-session startxfce4
EOF
RUN chmod +x /home/pilot/.vnc/xstartup

# ── Install LinuxPilot ───────────────────────────────────────
WORKDIR /home/pilot/LinuxPilot
COPY . .

# Create venv with system site-packages (for python3-gi, python3-seccomp)
RUN python3 -m venv --system-site-packages /home/pilot/.venv \
    && /home/pilot/.venv/bin/pip install --upgrade pip \
    && /home/pilot/.venv/bin/pip install -e ".[dev]"

# ── Workspace directory ──────────────────────────────────────
RUN mkdir -p /var/lib/linuxpilot \
    && mkdir -p /home/pilot/Downloads \
    && mkdir -p /home/pilot/Documents \
    && chown -R pilot:pilot /var/lib/linuxpilot /home/pilot

# ── Entrypoint script ────────────────────────────────────────
COPY desktop/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# cgroup v2 relaxation for unprivileged user namespaces
RUN echo 'kernel.apparmor_restrict_unprivileged_userns=0' > /etc/sysctl.d/60-lp.conf || true

# ── Ports ────────────────────────────────────────────────────
# 6080: noVNC (desktop)
# 8000: LinuxPilot API + dashboard
EXPOSE 6080 8000

# ── Run as pilot user ────────────────────────────────────────
USER pilot
ENV PATH="/home/pilot/.venv/bin:$PATH"

ENTRYPOINT ["/entrypoint.sh"]
