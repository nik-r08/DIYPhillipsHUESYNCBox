#!/usr/bin/env bash
# One-shot setup on Raspberry Pi OS (Bookworm, 64-bit recommended).
# Usage:  cd pi && ./setup_pi.sh
set -euo pipefail
cd "$(dirname "$0")"

echo "== apt packages =="
sudo apt-get update
sudo apt-get install -y python3-venv python3-dev libportaudio2 libatlas-base-dev \
    v4l-utils alsa-utils libgl1 libglib2.0-0

echo "== python venv =="
python3 -m venv venv --system-site-packages
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

if [ ! -f config.yaml ]; then
  cp config.example.yaml config.yaml
  echo "created config.yaml - edit it (LED counts, WLED host, capture device)"
fi

echo "== permissions =="
sudo usermod -aG video,audio,dialout,spi,gpio "$USER" || true

echo
echo "Run it now:   ./venv/bin/python -m syncbox --config config.yaml"
echo "Web UI:       http://$(hostname -I | awk '{print $1}'):8080"
echo "Autostart:    sudo cp syncbox.service /etc/systemd/system/ && sudo systemctl enable --now syncbox"
