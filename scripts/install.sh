#!/bin/bash

echo "Installing DoorBell Spotify System..."

sudo apt update
sudo apt install -y ffmpeg python3-pip python3-pygame curl

pip3 install -r requirements.txt

mkdir -p ~/doorbell_cache

echo "Copying systemd services..."

sudo cp services/*.service /etc/systemd/system/

sudo systemctl daemon-reload

sudo systemctl enable doorbell_cache_updater.service
sudo systemctl enable doorbell_spotify.service

echo "Setup complete!"
echo "IMPORTANT:"
echo "1. Copy .env.example to ~/.env"
echo "2. Edit ~/.env with your ntfy topic"
echo "3. Reboot system"

