#!/usr/bin/env bash
# start-kiosk.sh — Launch WDV kiosk app as a fullscreen session
# Place this in ~/.config/lxsession/LXDE-pi/autostart  OR
# enable the systemd service:  sudo systemctl enable wdv-kiosk.service

set -e

# Disable screen blanking and power saving
xset s off
xset -dpms
xset s noblank

# Hide the mouse cursor (unclutter must be installed)
# Uncomment if unclutter is available: unclutter -idle 0 &

# Change to app directory
cd /home/admin/water-dispenser-vendo/src/rpi/WDVHost

exec python3 main.py
