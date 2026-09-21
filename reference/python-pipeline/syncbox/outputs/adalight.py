"""Adalight protocol over USB serial.

Works with WLED (Settings > Sync > Serial, set the baud rate) and with the
minimal firmware in ``esp32/``.  Frame = b"Ada" + hi + lo + checksum + RGB...
where hi/lo is (led_count - 1) big-endian and checksum = hi ^ lo ^ 0x55.
"""
from __future__ import annotations

import numpy as np

from ..processor import apply_color_correction, resample_strip
from . import Output

try:
    import serial
except Exception:  # pragma: no cover
    serial = None


def build_adalight_frame(rgb_bytes: bytes) -> bytes:
    n = len(rgb_bytes) // 3
    count = max(n - 1, 0)
    hi, lo = (count >> 8) & 0xFF, count & 0xFF
    return b"Ada" + bytes([hi, lo, hi ^ lo ^ 0x55]) + rgb_bytes


class AdalightOutput(Output):
    name = "adalight"

    def __init__(self, cfg: dict):
        if serial is None:
            raise RuntimeError("pyserial is required for the Adalight output")
        self.port = serial.Serial(cfg.get("port", "/dev/ttyUSB0"), int(cfg.get("baud", 115200)), timeout=0, write_timeout=0.05)
        self.n_leds = int(cfg.get("leds", 0) or 0)
        self.correction = cfg.get("color_correction")
        self.error = None

    def send(self, colors: np.ndarray) -> None:
        if self.n_leds:
            colors = resample_strip(colors.astype(np.float32), self.n_leds).astype(np.uint8)
        colors = apply_color_correction(colors, self.correction)
        try:
            self.port.write(build_adalight_frame(colors.tobytes()))
            self.error = None
        except Exception as exc:
            self.error = str(exc)

    def close(self) -> None:
        self.port.close()
