#!/usr/bin/env bash
# Show the video and audio capture devices Linux can see.
set -e
echo "== Video devices (V4L2) =="
v4l2-ctl --list-devices 2>/dev/null || ls -l /dev/video* 2>/dev/null || echo "none (install v4l-utils)"
for d in /dev/video*; do
  [ -e "$d" ] || continue
  echo "--- $d formats ---"
  v4l2-ctl -d "$d" --list-formats-ext 2>/dev/null | grep -E "^\s+\[|Size|Interval" | head -20
done
echo
echo "== Audio capture devices (ALSA) =="
arecord -l 2>/dev/null || echo "none (install alsa-utils)"
echo
echo "== Audio devices as seen by sounddevice =="
python3 -c "import sounddevice as sd; print(sd.query_devices())" 2>/dev/null || echo "(pip install sounddevice)"
