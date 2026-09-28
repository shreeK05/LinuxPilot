#!/bin/bash
set -e

echo "=========================================="
echo "    Installing LinuxPilot for Ubuntu      "
echo "=========================================="

# 1. Update and install dependencies
echo "[1/5] Installing system dependencies..."
sudo apt update
sudo apt install -y python3 python3-venv python3-pip nodejs nginx curl

# 2. Setup Python Backend
echo "[2/5] Setting up Python backend..."
cd apps/api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd ../..

# 3. Setup React Frontend
echo "[3/5] Building React frontend..."
cd apps/web
npm install
chmod -R +x node_modules/.bin || true
npm run build
cd ../..

# 4. Install Background Services (Systemd & Nginx)
echo "[4/5] Installing background services..."

# Dynamically set the path in the service file based on where it was extracted
sed -e "s|/home/sahil/LinuxPilot|$PWD|g" -e "s|User=sahil|User=$USER|g" deployment/linuxpilot-api.service > /tmp/linuxpilot-api.service
sudo cp /tmp/linuxpilot-api.service /etc/systemd/system/linuxpilot-api.service

sudo systemctl daemon-reload
sudo systemctl enable linuxpilot-api
sudo systemctl restart linuxpilot-api

sed -e "s|/home/sahil/LinuxPilot|$PWD|g" deployment/linuxpilot.nginx.conf > /tmp/linuxpilot.nginx.conf
sudo cp /tmp/linuxpilot.nginx.conf /etc/nginx/sites-available/linuxpilot
if [ ! -f /etc/nginx/sites-enabled/linuxpilot ]; then
    sudo ln -s /etc/nginx/sites-available/linuxpilot /etc/nginx/sites-enabled/
fi
sudo rm -f /etc/nginx/sites-enabled/default
sudo systemctl restart nginx

# 5. Install Desktop Shortcut
echo "[5/5] Creating Ubuntu Application menu shortcut..."
sudo cp deployment/linuxpilot.desktop /usr/share/applications/
sudo chmod 644 /usr/share/applications/linuxpilot.desktop

echo "=========================================="
echo " Installation Complete! "
echo " LinuxPilot is now installed as an Ubuntu application."
echo " You can open it by searching for 'LinuxPilot' in your app menu,"
echo " or by navigating to http://localhost in your browser."
echo "=========================================="
