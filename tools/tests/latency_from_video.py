#!/usr/bin/env python3
"""Measure screen-to-LED latency from a slow-motion phone video (T1).

Film the TV and the LED glow on the wall in one shot at 240 fps (iPhone/Android "Slo-mo")
while latency_1080p60.mp4 plays. Then:

    python3 latency_from_video.py slomo.mov --screen x,y,w,h --strip x,y,w,h [--fps 240]

Regions are pixel rectangles in the phone video: one on the TV picture (not the counter),
one on the wall glow next to the strip. The script finds every black->white and white->black
transition in each region and reports the delay of the strip behind the screen, in ms.
If --fps is omitted the container's reported fps is used; phones sometimes store 30 fps
metadata for slo-mo files, so pass --fps 240 when in doubt.
"""
import argparse
import sys

import cv2
import numpy as np


def rect(s):
    x, y, w, h = (int(v) for v in s.split(","))
    return x, y, w, h


def transitions(signal, fps):
    """Frame indices where the normalised signal crosses 0.5, with direction."""
    s = (signal - signal.min()) / max(signal.max() - signal.min(), 1e-6)
    above = s > 0.5
    idx = np.flatnonzero(above[1:] != above[:-1]) + 1
    return [(int(i), "up" if above[i] else "down") for i in idx]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--screen", required=True, type=rect)
    ap.add_argument("--strip", required=True, type=rect)
    ap.add_argument("--fps", type=float)
    a = ap.parse_args()
    cap = cv2.VideoCapture(a.video)
    fps = a.fps or cap.get(cv2.CAP_PROP_FPS)
    sc, st = [], []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
        x, y, w, h = a.screen
        sc.append(float(g[y:y + h, x:x + w].mean()))
        x, y, w, h = a.strip
        st.append(float(g[y:y + h, x:x + w].mean()))
    sc, st = np.array(sc), np.array(st)
    if len(sc) < 10:
        sys.exit("could not read the video")
    ts, tt = transitions(sc, fps), transitions(st, fps)
    delays = []
    for i, d in ts:
        cands = [j for j, dd in tt if dd == d and 0 <= j - i <= fps]   # strip transition within 1 s after screen
        if cands:
            delays.append((cands[0] - i) / fps * 1000.0)
    if not delays:
        sys.exit("no matching transitions found; check the regions and --fps")
    delays = np.array(delays)
    print(f"video fps used: {fps:.1f}   screen transitions: {len(ts)}   matched: {len(delays)}")
    print(f"latency ms  mean {delays.mean():.1f}   median {np.median(delays):.1f}   min {delays.min():.1f}   max {delays.max():.1f}   p95 {np.percentile(delays, 95):.1f}")
    print("PASS (<= 80 ms median)" if np.median(delays) <= 80 else "FAIL (> 80 ms median)")


if __name__ == "__main__":
    main()
