#!/bin/bash -e
# Runs inside the image chroot: install the Sync Box from the repo checkout copied in by pi-gen.
mkdir -p /tmp/syncbox-src
cp -r /files/repo/. /tmp/syncbox-src/
SYNCBOX_SRC=/tmp/syncbox-src SYNCBOX_USER=pi bash /tmp/syncbox-src/installer/install.sh
rm -rf /tmp/syncbox-src
# the wizard must run on first boot; make sure the flag is clear
echo '{"wizard_done": false}' > /etc/syncbox/syncbox.json
