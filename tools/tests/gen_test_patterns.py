#!/usr/bin/env python3
"""Generate the colour / black-bar / dark-scene test video (T4, T5).

Sections (each --seconds long, default 6 s, 1080p30):
  1 solid red, green, blue, white, cyan, magenta, yellow (0.86 s each, repeated)
  2 split screen: left red / right blue, then top green / bottom magenta
  3 letterbox 2.39:1 with a moving colour gradient inside the bars
  4 pillarbox 4:3 with the same gradient
  5 dark scene: luma about 3 percent with faint colour, to check black stays black
  6 near-black with a bright object in the centre (bars must NOT be detected)
"""
import argparse

import cv2
import numpy as np


def gradient(w, h, t):
    xs = np.linspace(0, 1, w, dtype=np.float32)[None, :].repeat(h, 0)
    hue = ((xs + t * 0.1) % 1.0 * 179).astype(np.uint8)
    hsv = np.stack([hue, np.full((h, w), 255, np.uint8), np.full((h, w), 220, np.uint8)], -1)
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="patterns_1080p30.mp4")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--seconds", type=float, default=6)
    a = ap.parse_args()
    w, h = 1920, 1080
    writer = None
    for fourcc in ("avc1", "mp4v"):
        writer = cv2.VideoWriter(a.out, cv2.VideoWriter_fourcc(*fourcc), a.fps, (w, h))
        if writer.isOpened():
            break
    n = int(a.fps * a.seconds)
    solids = [(0, 0, 255), (0, 255, 0), (255, 0, 0), (255, 255, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255)]
    for i in range(n):
        writer.write(np.full((h, w, 3), solids[(i * len(solids)) // n], np.uint8))
    for i in range(n):
        f = np.zeros((h, w, 3), np.uint8)
        if i < n // 2:
            f[:, : w // 2] = (0, 0, 255); f[:, w // 2:] = (255, 0, 0)
        else:
            f[: h // 2] = (0, 255, 0); f[h // 2:] = (255, 0, 255)
        writer.write(f)
    bar = int((h - w / 2.39) / 2)
    for i in range(n):
        f = np.zeros((h, w, 3), np.uint8); f[bar:h - bar] = gradient(w, h - 2 * bar, i / a.fps); writer.write(f)
    pil = int((w - h * 4 / 3) / 2)
    for i in range(n):
        f = np.zeros((h, w, 3), np.uint8); f[:, pil:w - pil] = gradient(w - 2 * pil, h, i / a.fps); writer.write(f)
    for i in range(n):
        f = np.full((h, w, 3), 8, np.uint8); f[:, : w // 3] = (12, 6, 6); writer.write(f)
    for i in range(n):
        f = np.full((h, w, 3), 4, np.uint8); cv2.circle(f, (w // 2, h // 2), 150, (255, 255, 255), -1); writer.write(f)
    writer.release()
    print("wrote", a.out)


if __name__ == "__main__":
    main()
