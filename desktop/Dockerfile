FROM ubuntu:24.04

# Install system dependencies
RUN apt-get update && apt-get install -y \
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
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Create user
RUN useradd -m -s /bin/bash agent
RUN echo "agent ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Set up workspace
RUN mkdir -p /var/lib/linuxpilot && chown agent:agent /var/lib/linuxpilot

# Configure accessibility
RUN echo 'export GTK_MODULES=gail:atk-bridge' >> /home/agent/.bashrc
RUN echo 'export QT_LINUX_ACCESSIBILITY_ALWAYS_ON=1' >> /home/agent/.bashrc
RUN echo 'export ACCESSIBILITY_ENABLED=1' >> /home/agent/.bashrc

# Relax AppArmor for user namespaces
RUN echo 'kernel.apparmor_restrict_unprivileged_userns=0' >> /etc/sysctl.d/60-lp.conf

# Switch to agent user
USER agent
WORKDIR /home/agent

# Copy LinuxPilot (would be done in production)
# COPY . /home/agent/LinuxPilot

# Expose VNC port
EXPOSE 5900
EXPOSE 6080

# Start script
COPY start.sh /home/agent/start.sh
RUN chmod +x /home/agent/start.sh

CMD ["/home/agent/start.sh"]
