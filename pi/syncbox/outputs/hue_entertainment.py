"""Philips Hue Entertainment streaming (Hue Bridge v2, CLIP v2 + DTLS).

How it works
------------
1. You pair once (tools/hue_pair.py): the bridge returns an *application key*
   and a *client key* (PSK).  You also create an Entertainment Area in the Hue
   app that contains the lights you want to sync.
2. On start we PUT ``{"action": "start"}`` on the entertainment configuration,
   which puts those lights into streaming mode.
3. We open a DTLS 1.2 session (PSK, TLS_PSK_WITH_AES_128_GCM_SHA256) to UDP
   port 2100 and send colour messages at up to 25 Hz:

       "HueStream" | 0x02 0x00 (version) | seq | 0x00 0x00 | colour space
       (0x00 = RGB) | 0x00 | 36-byte entertainment configuration id |
       then per channel: channel id (1 byte) + R, G, B as 16-bit big-endian.

4. Each Hue channel has a position (x = left/right, y = back/front, z =
   down/up).  We map it to the LED zone at the matching angle around the
   screen, so a Play bar on the left shows the left edge of the picture.

Requires ``python-mbedtls`` (pip install python-mbedtls) and ``requests``.
"""
from __future__ import annotations

import math
import socket
import struct
import time
import warnings

import numpy as np

from ..zones import nearest_zone_for_angle, zone_angles
from . import Output

try:
    import requests
    from urllib3.exceptions import InsecureRequestWarning
    warnings.simplefilter("ignore", InsecureRequestWarning)
except Exception:  # pragma: no cover
    requests = None

try:
    from mbedtls import tls
except Exception:  # pragma: no cover
    tls = None

HUE_STREAM_PORT = 2100


def build_hue_message(entertainment_id: str, seq: int, channel_colors: list[tuple[int, tuple[int, int, int]]]) -> bytes:
    """Serialise one Entertainment API v2 RGB message."""
    eid = entertainment_id.encode("ascii")
    if len(eid) != 36:
        raise ValueError("entertainment configuration id must be a 36-char UUID")
    msg = bytearray(b"HueStream")
    msg += b"\x02\x00"           # protocol version 2.0
    msg += bytes([seq & 0xFF])   # sequence id (ignored by bridge, useful for debugging)
    msg += b"\x00\x00"           # reserved
    msg += b"\x00"               # colour space: 0 = RGB, 1 = xy + brightness
    msg += b"\x00"               # reserved
    msg += eid
    for channel_id, (r, g, b) in channel_colors:
        msg += bytes([channel_id & 0xFF]) + struct.pack(">HHH", r * 257, g * 257, b * 257)
    return bytes(msg)


def map_channels_to_zones(channels: list[dict], rects: np.ndarray, overrides: dict | None = None) -> list[tuple[int, int]]:
    """[(channel_id, led_index)] using each channel's position around the screen."""
    angles = zone_angles(rects)
    overrides = {int(k): int(v) for k, v in (overrides or {}).items()}
    use_z = any(abs(float(c.get("position", {}).get("z", 0.0))) > 0.05 for c in channels)
    mapping = []
    for ch in channels:
        cid = int(ch["channel_id"])
        if cid in overrides:
            mapping.append((cid, overrides[cid] % len(rects)))
            continue
        pos = ch.get("position", {})
        x = float(pos.get("x", 0.0))
        vertical = float(pos.get("z", 0.0)) if use_z else float(pos.get("y", 0.0))
        angle = math.atan2(vertical, x) if (abs(x) > 1e-3 or abs(vertical) > 1e-3) else math.pi / 2
        mapping.append((cid, nearest_zone_for_angle(angles, angle)))
    return mapping


class HueEntertainmentOutput(Output):
    name = "hue"

    def __init__(self, cfg: dict, rects: np.ndarray):
        if requests is None or tls is None:
            raise RuntimeError("Hue output needs: pip install requests python-mbedtls")
        self.bridge = cfg["bridge"]
        self.app_key = cfg["app_key"]
        self.client_key = cfg["client_key"]
        self.eid = cfg["entertainment_id"]
        self.min_interval = 1.0 / float(cfg.get("max_rate", 25))
        self.overrides = cfg.get("channel_map") or {}
        self.rects = rects
        self.mapping: list[tuple[int, int]] = []
        self.sock = None
        self.seq = 0
        self.last_send = 0.0
        self.error: str | None = None
        self._start()

    # -- CLIP v2 helpers ------------------------------------------------------
    def _url(self) -> str:
        return f"https://{self.bridge}/clip/v2/resource/entertainment_configuration/{self.eid}"

    def _headers(self) -> dict:
        return {"hue-application-key": self.app_key}

    def _start(self) -> None:
        # NOTE: verify=False because the bridge uses a self-signed certificate.
        # For a hardened setup download the Hue root CA and pass verify=<path>.
        r = requests.get(self._url(), headers=self._headers(), verify=False, timeout=5)
        r.raise_for_status()
        cfg = r.json()["data"][0]
        self.mapping = map_channels_to_zones(cfg.get("channels", []), self.rects, self.overrides)
        r = requests.put(self._url(), headers=self._headers(), json={"action": "start"}, verify=False, timeout=5)
        r.raise_for_status()

        conf = tls.DTLSConfiguration(
            pre_shared_key=(self.app_key, bytes.fromhex(self.client_key)),
            ciphers=["TLS-PSK-WITH-AES-128-GCM-SHA256"],
            validate_certificates=False,
        )
        ctx = tls.ClientContext(conf)
        sock = ctx.wrap_socket(socket.socket(socket.AF_INET, socket.SOCK_DGRAM), server_hostname=None)
        sock.settimeout(2.0)
        sock.connect((self.bridge, HUE_STREAM_PORT))
        for _ in range(100):             # handshake may need a few retries
            try:
                sock.do_handshake()
                break
            except (tls.WantReadError, tls.WantWriteError):
                time.sleep(0.02)
        self.sock = sock

    def send(self, colors: np.ndarray) -> None:
        now = time.monotonic()
        if now - self.last_send < self.min_interval or self.sock is None:
            return
        self.last_send = now
        channel_colors = [(cid, tuple(int(v) for v in colors[idx])) for cid, idx in self.mapping]
        try:
            self.sock.send(build_hue_message(self.eid, self.seq, channel_colors))
            self.seq = (self.seq + 1) & 0xFF
            self.error = None
        except Exception as exc:
            self.error = str(exc)

    def close(self) -> None:
        try:
            if self.sock is not None:
                self.sock.close()
            requests.put(self._url(), headers=self._headers(), json={"action": "stop"}, verify=False, timeout=5)
        except Exception:
            pass
