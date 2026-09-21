#!/usr/bin/env bash
# Build a flashable Sync Box image with pi-gen (https://github.com/RPi-Distro/pi-gen, arm64 branch).
# Output: deploy/image_*-syncbox.img.xz  Flash with Raspberry Pi Imager; set Wi-Fi/user in Imager's settings.
# Run on a Debian/Ubuntu x86 host with Docker, or on a Pi. Takes 30-60 min.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
WORK=${WORK:-$HERE/work}
mkdir -p "$WORK"; cd "$WORK"
[ -d pi-gen ] || git clone --depth 1 --branch arm64 https://github.com/RPi-Distro/pi-gen.git
cd pi-gen
cat > config <<CFG
IMG_NAME=syncbox
RELEASE=${RELEASE:-bookworm}
DEPLOY_COMPRESSION=xz
TARGET_HOSTNAME=syncbox
FIRST_USER_NAME=pi
FIRST_USER_PASS=syncbox
ENABLE_SSH=1
STAGE_LIST="stage0 stage1 stage2 $HERE/pi-gen-stage"
CFG
# stage2 = Pi OS Lite. Skip the desktop stages.
touch stage3/SKIP stage4/SKIP stage5/SKIP 2>/dev/null || true
rm -f stage2/EXPORT_NOOBS 2>/dev/null || true
if command -v docker >/dev/null; then ./build-docker.sh; else sudo ./build.sh; fi
ls -la deploy/
