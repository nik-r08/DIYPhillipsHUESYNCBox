#!/usr/bin/env bash
# T0: time from power-on to HyperHDR streaming. Run after a cold boot.
echo "-- firmware+kernel+userspace (systemd-analyze, excludes ~3-5 s of bootloader on Pi 5):"
systemd-analyze 2>/dev/null | head -1
U=$(ls /home | head -1)
echo "-- HyperHDR started at (seconds after kernel start):"
journalctl -u "hyperhdr@$U" -b --no-pager -o short-monotonic 2>/dev/null | grep -m1 Started | awk '{print $1}'
echo "-- syncbox-ui started at:"
journalctl -u syncbox-ui -b --no-pager -o short-monotonic 2>/dev/null | grep -m1 Started | awk '{print $1}'
echo "-- first grabber frame (HyperHDR log):"
journalctl -u "hyperhdr@$U" -b --no-pager -o short-monotonic 2>/dev/null | grep -im1 -E "grabber|V4L2|started" | awk '{print $1}'
echo "Add ~4 s for the bootloader. Target: LEDs following the screen within 30 s of power-on (stopwatch check counts too)."
