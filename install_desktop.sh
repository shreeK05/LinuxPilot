#!/bin/bash
set -e

echo "==========================================="
echo " Installing LinuxPilot Desktop Application   "
echo "==========================================="

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Remove any existing installation
echo "-> Removing previous installation..."
rm -f ~/.local/share/applications/linuxpilot.desktop

# Create the desktop entry
echo "-> Creating application shortcut..."
cat > ~/.local/share/applications/linuxpilot.desktop << EOL
[Desktop Entry]
Version=1.0
Type=Application
Name=LinuxPilot
Comment=Agentic Linux Automation
Exec=$DIR/start.sh
Icon=utilities-terminal
Terminal=true
Categories=Utility;System;
EOL

chmod +x ~/.local/share/applications/linuxpilot.desktop
chmod +x "$DIR/start.sh"

echo "-> Installation complete!"
echo "-> You can now launch LinuxPilot from your application menu."
