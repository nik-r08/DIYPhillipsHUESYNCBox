#!/usr/bin/env bash
# Read-only root with persistent HyperHDR + syncbox data.
#
# Raspberry Pi OS's overlay option (raspi-config > Performance > Overlay File System,
# package `overlayroot`) makes / a tmpfs overlay so a power cut cannot corrupt the SD card.
# It also makes HyperHDR's settings vanish on reboot. We keep them by storing them on
# the FAT boot partition (/boot/firmware, which stays writable) and bind-mounting that
# directory over the user's ~/.hyperhdr and /etc/syncbox. FAT has no permissions, so
# the bind source is mounted with uid/gid of the user.
#
#   sudo syncbox-persist enable    # after the wizard and calibration are done
#   sudo syncbox-persist disable   # to make changes to the OS (apt, editing files)
#   sudo syncbox-persist status
set -euo pipefail
SB_USER="${SYNCBOX_USER:-$(logname 2>/dev/null || echo pi)}"
HOME_DIR=$(getent passwd "$SB_USER" | cut -d: -f6)
BOOT=/boot/firmware; [ -d $BOOT ] || BOOT=/boot
DATA=$BOOT/syncbox-data
UNIT=/etc/systemd/system/syncbox-data.mount

case "${1:-status}" in
  enable)
    mkdir -p "$DATA/hyperhdr" "$DATA/etc"
    # seed with current data
    [ -d "$HOME_DIR/.hyperhdr" ] && cp -a "$HOME_DIR/.hyperhdr/." "$DATA/hyperhdr/" || true
    cp -a /etc/syncbox/. "$DATA/etc/" || true
    # bind mounts (FAT: ownership is fixed at mount time by the vfat mount of /boot/firmware,
    # which Pi OS mounts root-owned; HyperHDR runs as $SB_USER, so re-mount the boot partition
    # with uid/gid of that user)
    sed -i "s#^\(\S\+\s\+$BOOT\s\+vfat\s\+\)\(\S\+\)#\1\2,uid=$(id -u $SB_USER),gid=$(id -g $SB_USER)#" /etc/fstab
    grep -q "syncbox-data/hyperhdr" /etc/fstab || cat >> /etc/fstab <<FST
$DATA/hyperhdr  $HOME_DIR/.hyperhdr  none  bind  0 0
$DATA/etc       /etc/syncbox         none  bind  0 0
FST
    mkdir -p "$HOME_DIR/.hyperhdr"; chown "$SB_USER":"$SB_USER" "$HOME_DIR/.hyperhdr"
    # enable overlay root (raspi-config non-interactive: 0 = enable). Also write-protects /boot? No: keep boot writable (arg 1).
    raspi-config nonint do_overlayfs 0
    # do_overlayfs may also offer to protect the boot partition; we need it writable:
    sed -i 's/ ro,/ rw,/' /etc/fstab || true
    echo "Overlay root enabled. Reboot to activate. HyperHDR data now lives in $DATA."
    ;;
  disable)
    raspi-config nonint do_overlayfs 1
    echo "Overlay root disabled. Reboot, make your changes, then 'syncbox-persist enable' again."
    ;;
  status)
    if grep -q overlayroot /proc/cmdline 2>/dev/null || mount | grep -q 'overlayroot'; then echo "overlay root: ACTIVE (SD card protected)"; else echo "overlay root: inactive"; fi
    mount | grep -E "syncbox-data" || echo "no persistent bind mounts active"
    ;;
  *) echo "usage: syncbox-persist enable|disable|status"; exit 1;;
esac
