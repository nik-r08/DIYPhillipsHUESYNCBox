"""Video capture thread.

Reads frames from a V4L2 device (USB HDMI capture card) as fast as it can and
keeps only the newest one, so the processing loop never works on a stale
frame.  Also supports ``synthetic`` (moving test pattern) and ``file:`` sources
for development without any hardware.
"""
from __future__ import annotations

import math
import threading
import time

import numpy as np

try:
    import cv2
except Exception:  # pragma: no cover
    cv2 = None


class SyntheticSource:
    """Rotating colour wheel with a bright moving blob - good for testing."""

    def __init__(self, width: int, height: int, fps: int):
        self.w, self.h, self.fps = width, height, fps
        yy, xx = np.mgrid[0:height, 0:width]
        self.angle = np.arctan2(yy - height / 2, xx - width / 2)
        self.t0 = time.monotonic()

    def read(self):
        t = time.monotonic() - self.t0
        hue = ((self.angle / (2 * math.pi)) + t * 0.1) % 1.0
        # cheap HSV->RGB with s=v=1
        h6 = hue * 6
        x = 1 - np.abs(h6 % 2 - 1)
        i = h6.astype(int) % 6
        r = np.choose(i, [1, x, 0, 0, x, 1])
        g = np.choose(i, [x, 1, 1, x, 0, 0])
        b = np.choose(i, [0, 0, x, 1, 1, x])
        frame = (np.stack([b, g, r], axis=-1) * 200).astype(np.uint8)   # BGR like OpenCV
        time.sleep(1.0 / self.fps)
        return True, frame

    def release(self):
        pass


class FileSource:
    """Loops a video file at its native frame rate (requires OpenCV)."""

    def __init__(self, path: str):
        if cv2 is None:
            raise RuntimeError("OpenCV is required for file sources")
        self.path = path
        self.cap = cv2.VideoCapture(path)
        self.delay = 1.0 / max(self.cap.get(cv2.CAP_PROP_FPS) or 25.0, 1.0)

    def read(self):
        ok, frame = self.cap.read()
        if not ok:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ok, frame = self.cap.read()
        time.sleep(self.delay)
        return ok, frame

    def release(self):
        self.cap.release()


def open_v4l2(device, width: int, height: int, fps: int, fourcc: str):
    if cv2 is None:
        raise RuntimeError("OpenCV is required for V4L2 capture (pip install opencv-python-headless)")
    dev = int(device) if str(device).isdigit() else str(device)
    cap = cv2.VideoCapture(dev, cv2.CAP_V4L2)
    if not cap.isOpened():
        raise RuntimeError(f"cannot open capture device {device}")
    if fourcc:
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*fourcc))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    cap.set(cv2.CAP_PROP_FPS, fps)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)   # keep latency down
    return cap


class Capture(threading.Thread):
    def __init__(self, cfg: dict):
        super().__init__(name="capture", daemon=True)
        self.cfg = cfg
        self._lock = threading.Lock()
        self._frame = None
        self._seq = 0
        self._ts = 0.0
        self._stop = threading.Event()
        self.fps = 0.0
        self.error: str | None = None
        self.actual_size = (0, 0)

    # -- public API -----------------------------------------------------------
    def latest(self):
        with self._lock:
            return self._frame, self._seq, self._ts

    def stop(self):
        self._stop.set()

    # -- internals ------------------------------------------------------------
    def _open(self):
        device = self.cfg.get("device", "/dev/video0")
        w, h, fps = int(self.cfg.get("width", 640)), int(self.cfg.get("height", 360)), int(self.cfg.get("fps", 30))
        if device == "synthetic":
            return SyntheticSource(w, h, fps)
        if isinstance(device, str) and device.startswith("file:"):
            return FileSource(device[5:])
        return open_v4l2(device, w, h, fps, self.cfg.get("fourcc", "MJPG"))

    def run(self):
        src = None
        fails = 0
        t_last, n = time.monotonic(), 0
        while not self._stop.is_set():
            if src is None:
                try:
                    src = self._open()
                    self.error = None
                except Exception as exc:
                    self.error = str(exc)
                    time.sleep(2.0)
                    continue
            ok, frame = src.read()
            if not ok or frame is None:
                fails += 1
                if fails > 30:              # ~1 s of failures: reopen device
                    try:
                        src.release()
                    except Exception:
                        pass
                    src, fails = None, 0
                    self.error = "no frames from capture device, reopening"
                time.sleep(0.03)
                continue
            fails = 0
            with self._lock:
                self._frame = frame
                self._seq += 1
                self._ts = time.monotonic()
                self.actual_size = (frame.shape[1], frame.shape[0])
            n += 1
            now = time.monotonic()
            if now - t_last >= 1.0:
                self.fps = n / (now - t_last)
                t_last, n = now, 0
        if src is not None:
            src.release()
