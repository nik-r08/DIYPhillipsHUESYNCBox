#!/usr/bin/env python3
"""Generate the latency test video: full-frame black/white flashes with a visible frame counter.

    python3 gen_latency_video.py --out latency_1080p60.mp4 --fps 60 --seconds 30 --period 1.0

Play it on the source (PS5 Media Player from a USB stick; re-encode to H.264 if the PS5
refuses the file:  ffmpeg -i latency_1080p60.mp4 -c:v libx264 -pix_fmt yuv420p -crf 12 latency_h264.mp4).
Film TV and LED strip together at 240 fps slow motion, then run latency_from_video.py.
"""
import argparse

import cv2
import numpy as np


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="latency_1080p60.mp4")
    ap.add_argument("--fps", type=int, default=60)
    ap.add_argument("--seconds", type=float, default=30)
    ap.add_argument("--period", type=float, default=1.0, help="seconds per black or white phase")
    ap.add_argument("--size", default="1920x1080")
    a = ap.parse_args()
    w, h = (int(v) for v in a.size.split("x"))
    n = int(a.fps * a.seconds)
    writer = None
    for fourcc in ("avc1", "mp4v"):
        writer = cv2.VideoWriter(a.out, cv2.VideoWriter_fourcc(*fourcc), a.fps, (w, h))
        if writer.isOpened():
            print("codec:", fourcc)
            break
    if writer is None or not writer.isOpened():
        raise SystemExit("no usable codec in this OpenCV build; install ffmpeg and use it instead")
    per = int(a.fps * a.period)
    for i in range(n):
        white = (i // per) % 2 == 1
        frame = np.full((h, w, 3), 255 if white else 0, dtype=np.uint8)
        # small counter in the centre, inverted colour, so the edges (what the LEDs sample) stay pure
        cv2.putText(frame, f"{i:05d}", (w // 2 - 120, h // 2 + 30), cv2.FONT_HERSHEY_SIMPLEX, 2.0,
                    (0, 0, 0) if white else (255, 255, 255), 4)
        writer.write(frame)
    writer.release()
    print(f"wrote {a.out}: {n} frames, {a.fps} fps, phase {a.period}s")


if __name__ == "__main__":
    main()
