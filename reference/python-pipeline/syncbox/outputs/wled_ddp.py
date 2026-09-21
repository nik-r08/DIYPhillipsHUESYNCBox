"""WLED over Wi-Fi/Ethernet using the DDP protocol (UDP port 4048).

WLED treats DDP as a *realtime* stream: it shows exactly what we send and,
when packets stop for `Realtime timeout` (Settings > Sync, default 2.5 s), it
falls back to whatever preset/effect it was running before.  That is the
"static colour fallback" for free.
"""
from __future__ import annotations

import socket
import struct

import numpy as np

from ..processor import apply_color_correction, resample_strip
from . import Output

DDP_PORT = 4048
DDP_MAX_PIXELS = 480           # 1440 bytes of RGB per packet
DDP_FLAGS_VER1 = 0x40
DDP_FLAGS_PUSH = 0x01
DDP_TYPE_RGB24 = 0x0B          # RGB, 8 bits per channel
DDP_ID_DISPLAY = 0x01


def build_ddp_packets(rgb_bytes: bytes, seq: int = 0) -> list[bytes]:
    """Split an RGB byte string into DDP packets; PUSH is set on the last one."""
    packets = []
    total = len(rgb_bytes)
    chunk = DDP_MAX_PIXELS * 3
    offset = 0
    while offset < total or (total == 0 and not packets):
        data = rgb_bytes[offset:offset + chunk]
        last = offset + len(data) >= total
        flags = DDP_FLAGS_VER1 | (DDP_FLAGS_PUSH if last else 0)
        header = struct.pack(">BBBBIH", flags, seq & 0x0F, DDP_TYPE_RGB24, DDP_ID_DISPLAY, offset, len(data))
        packets.append(header + data)
        offset += len(data)
    return packets


class WLEDOutput(Output):
    name = "wled"

    def __init__(self, cfg: dict):
        self.host = cfg.get("host", "wled.local")
        self.port = int(cfg.get("port", DDP_PORT))
        self.n_leds = int(cfg.get("leds", 0) or 0)
        self.correction = cfg.get("color_correction")
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.seq = 1
        self._addr = None
        self.error: str | None = None

    def _resolve(self):
        if self._addr is None:
            self._addr = (socket.gethostbyname(self.host), self.port)
        return self._addr

    def send(self, colors: np.ndarray) -> None:
        if self.n_leds:
            colors = resample_strip(colors.astype(np.float32), self.n_leds).astype(np.uint8)
        colors = apply_color_correction(colors, self.correction)
        try:
            addr = self._resolve()
            for pkt in build_ddp_packets(colors.tobytes(), self.seq):
                self.sock.sendto(pkt, addr)
            self.seq = self.seq % 15 + 1
            self.error = None
        except OSError as exc:
            self.error = str(exc)
            self._addr = None

    def close(self) -> None:
        self.sock.close()
