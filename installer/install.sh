#!/usr/bin/env bash
# DIY Sync Box one-line installer for Raspberry Pi OS Lite (64-bit, Bookworm or Trixie).
#   curl -fsSL https://raw.githubusercontent.com/nik-r08/DIYPhillipsHUESYNCBox/main/installer/install.sh | sudo bash
# Idempotent: safe to re-run. Everything it does is logged to /var/log/syncbox-install.log.
#
# What it sets up (see docs/04 and docs/05):
#   1. HyperHDR from the author's apt repository            (engine)
#   2. syncbox-ui  : phone-sized control page on port 80    (this repo)
#   3. syncbox-status : front-panel LED on GPIO17            (this repo)
#   4. hostname syncbox + mDNS (syncbox.local), Wi-Fi power-save off
#   5. hardware watchdog (14 s), journald in RAM, usb_max_current_enable
#   6. optional: read-only root with persistent HyperHDR data (installer/persist.sh)
set -euo pipefail
exec > >(tee -a /var/log/syncbox-install.log) 2>&1

REPO_RAW="${SYNCBOX_REPO_RAW:-https://raw.githubusercontent.com/nik-r08/DIYPhillipsHUESYNCBox/main}"
SRC_DIR="${SYNCBOX_SRC:-}"           # set to a local checkout to install from it instead of downloading
SB_USER="${SYNCBOX_USER:-$(logname 2>/dev/null || echo pi)}"
BOOT_DIR=/boot/firmware; [ -d "$BOOT_DIR" ] || BOOT_DIR=/boot

[ "$(id -u)" = 0 ] || { echo "run with sudo"; exit 1; }
ARCH=$(dpkg --print-architecture)
[ "$ARCH" = arm64 ] || echo "WARNING: arch is $ARCH; HyperHDR publishes arm64 and armhf packages, 64-bit is recommended"

echo "== [1/6] packages"
apt-get update
apt-get install -y --no-install-recommends curl gnupg ca-certificates avahi-daemon v4l-utils alsa-utils \
    python3 python3-flask python3-requests python3-gpiozero python3-lgpio jq

echo "== [2/6] HyperHDR apt repository (https://github.com/awawa-dev/HyperHDR/wiki/Installation)"
if [ ! -f /usr/share/keyrings/hyperhdr.public.apt.gpg.key ]; then
    curl -fsSL https://awawa-dev.github.io/hyperhdr.public.apt.gpg.key -o /usr/share/keyrings/hyperhdr.public.apt.gpg.key
fi
CODENAME=$(. /etc/os-release && echo "${VERSION_CODENAME}")
echo "deb [signed-by=/usr/share/keyrings/hyperhdr.public.apt.gpg.key] https://awawa-dev.github.io/ ${CODENAME} main" \
    > /etc/apt/sources.list.d/hyperhdr.list
apt-get update
# keep the previously installed .deb for rollback (see syncbox-rollback)
mkdir -p /var/lib/syncbox/debs
if dpkg -s hyperhdr >/dev/null 2>&1; then
    CUR=$(dpkg-query -W -f='${Version}' hyperhdr)
    apt-get install -y --download-only --reinstall hyperhdr >/dev/null 2>&1 || true
    cp -n /var/cache/apt/archives/hyperhdr_*${CUR}*.deb /var/lib/syncbox/debs/ 2>/dev/null || true
fi
apt-get install -y hyperhdr
cp -n /var/cache/apt/archives/hyperhdr_*.deb /var/lib/syncbox/debs/ 2>/dev/null || true
usermod -aG video,audio,dialout,plugdev,gpio "$SB_USER" || true
systemctl enable "hyperhdr@${SB_USER}.service"

echo "== [3/6] syncbox files"
fetch() {  # fetch <repo-relative-path> <dest>
    if [ -n "$SRC_DIR" ]; then install -D -m "${3:-644}" "$SRC_DIR/$1" "$2"; else curl -fsSL "$REPO_RAW/$1" -o "$2"; chmod "${3:-644}" "$2"; fi
}
mkdir -p /opt/syncbox/ui/templates /etc/syncbox
fetch installer/syncbox-ui/app.py            /opt/syncbox/ui/app.py
fetch installer/syncbox-ui/hyperhdr.py       /opt/syncbox/ui/hyperhdr.py
fetch installer/syncbox-ui/templates/index.html    /opt/syncbox/ui/templates/index.html
fetch installer/syncbox-ui/templates/wizard.html   /opt/syncbox/ui/templates/wizard.html
fetch installer/syncbox-ui/templates/advanced.html /opt/syncbox/ui/templates/advanced.html
fetch installer/bin/syncbox-status.py        /opt/syncbox/syncbox-status.py
fetch installer/bin/syncbox-update           /usr/local/bin/syncbox-update 755
fetch installer/bin/syncbox-rollback         /usr/local/bin/syncbox-rollback 755
fetch installer/bin/syncbox-cec              /usr/local/bin/syncbox-cec 755
fetch installer/bin/syncbox-doctor           /usr/local/bin/syncbox-doctor 755
fetch installer/persist.sh                   /usr/local/sbin/syncbox-persist 755
fetch installer/systemd/syncbox-ui.service       /etc/systemd/system/syncbox-ui.service
fetch installer/systemd/syncbox-status.service   /etc/systemd/system/syncbox-status.service
fetch installer/systemd/syncbox-cec.service      /etc/systemd/system/syncbox-cec.service
fetch installer/hyperhdr-defaults.json       /etc/syncbox/hyperhdr-defaults.json
sed -i "s/__USER__/${SB_USER}/g" /etc/systemd/system/syncbox-*.service
[ -f /etc/syncbox/syncbox.json ] || echo '{"wizard_done": false, "tv_inches": 55, "mode": "video", "hue_enabled": false}' > /etc/syncbox/syncbox.json
chown -R "$SB_USER":"$SB_USER" /etc/syncbox /opt/syncbox

echo "== [4/6] hostname, mDNS, Wi-Fi power save"
if [ "$(hostname)" != syncbox ]; then hostnamectl set-hostname syncbox; sed -i 's/127.0.1.1.*/127.0.1.1\tsyncbox/' /etc/hosts; fi
systemctl enable --now avahi-daemon
mkdir -p /etc/NetworkManager/conf.d
printf '[connection]\nwifi.powersave = 2\n' > /etc/NetworkManager/conf.d/syncbox-wifi.conf   # 2 = disable
# reconnect: NetworkManager retries by default; make sure it never gives up
printf '[main]\nautoconnect-retries-default=0\n' > /etc/NetworkManager/conf.d/syncbox-retry.conf

echo "== [5/6] boot config, watchdog, journald"
CFG="$BOOT_DIR/config.txt"
grep -q '^usb_max_current_enable=1' "$CFG" || echo 'usb_max_current_enable=1' >> "$CFG"   # Pi 5 powered from the header: no PD negotiation
grep -q '^dtparam=watchdog=on' "$CFG" || echo 'dtparam=watchdog=on' >> "$CFG"
grep -q '^dtoverlay=disable-bt' "$CFG" || echo 'dtoverlay=disable-bt' >> "$CFG"       # not used, frees a UART and boot time
grep -q '^boot_delay=0' "$CFG" || echo 'boot_delay=0' >> "$CFG"
sed -i 's/^#\?RuntimeWatchdogSec=.*/RuntimeWatchdogSec=14/' /etc/systemd/system.conf        # bcm2835_wdt max is 15 s
sed -i 's/^#\?ShutdownWatchdogSec=.*/ShutdownWatchdogSec=2min/' /etc/systemd/system.conf
mkdir -p /etc/systemd/journald.conf.d
printf '[Journal]\nStorage=volatile\nRuntimeMaxUse=32M\n' > /etc/systemd/journald.conf.d/syncbox.conf
# faster boot: no waiting for network at boot, no swap file churn
systemctl disable --now dphys-swapfile 2>/dev/null || true
systemctl disable NetworkManager-wait-online.service 2>/dev/null || true

echo "== [6/6] services"
systemctl daemon-reload
systemctl enable --now syncbox-ui.service syncbox-status.service
systemctl enable syncbox-cec.service   # starts only if /dev/cec0 has a valid address; harmless otherwise
systemctl restart "hyperhdr@${SB_USER}.service" || true

echo
echo "Done. Open http://syncbox.local/  (first boot shows the setup wizard)."
echo "HyperHDR's own UI: http://syncbox.local:8090/"
echo "To lock the SD card read-only after setup:  sudo syncbox-persist enable"
echo "Reboot now to apply config.txt changes:      sudo reboot"
