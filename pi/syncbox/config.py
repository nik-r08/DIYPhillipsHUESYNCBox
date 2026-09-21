"""Configuration handling.

A single YAML file holds every tunable.  ``Config.snapshot()`` returns a deep
copy that the processing loop reads once per frame, so the web UI can update
settings at any time without locking the hot path.
"""
from __future__ import annotations

import copy
import threading
from pathlib import Path
from typing import Any

import yaml

DEFAULTS: dict[str, Any] = {
    "target_fps": 30,
    "capture": {
        # /dev/videoN, an integer index, "synthetic" (test pattern) or
        # "file:/path/to/video.mp4" (loops a video file, handy for testing).
        "device": "/dev/video0",
        "width": 640,
        "height": 360,
        "fps": 30,
        "fourcc": "MJPG",
        # Frames are shrunk to this width (16:9) before colour analysis.
        "sample_width": 256,
        "black_bar_detection": True,
        "signal_timeout": 3.0,   # seconds without a new frame -> "no signal"
        "black_timeout": 30.0,   # seconds of solid black -> "no signal"
    },
    "leds": {
        "top": 72,
        "right": 40,
        "bottom": 72,
        "left": 40,
        "start": "bottom-left",       # corner where LED #0 sits
        "direction": "clockwise",     # clockwise | counterclockwise (viewed from the front)
        "offset": 0,                  # LED #0 is this many LEDs past the start corner
        "border": 0.08,               # fraction of the frame edge sampled per LED
    },
    "processing": {
        "mode": "video",              # game | video | movie | music | static | calibrate
        "intensity": "high",          # subtle | moderate | high | extreme
        "brightness": 0.8,            # 0..1 global brightness
        "saturation": 1.3,            # 1.0 = as captured, >1 = more vivid
        "gamma": 2.2,
        "black_threshold": 12,        # 0..255, kills sensor noise "glow" in dark scenes
        "content_brightness": True,   # scale brightness with scene luminance
        "spatial_smoothing": 1,       # 0..3 neighbouring-LED blur passes
        "modes": {
            "game": {"tau_up": 0.02, "tau_down": 0.06},
            "video": {"tau_up": 0.08, "tau_down": 0.20},
            "movie": {"tau_up": 0.30, "tau_down": 0.60},
        },
        "static_color": [255, 140, 40],
    },
    "fallback": {
        "when_no_signal": "static",   # static | off | music
        "color": [40, 20, 80],
    },
    "audio": {
        "enabled": False,
        "device": None,               # sounddevice index/name, None = default input
        "samplerate": 48000,
        "channels": 2,
        "blocksize": 1024,
        "ms2109_fix": False,          # capture card reports 96 kHz mono but is 48 kHz stereo
        "sensitivity": 1.0,
        "react_in_video": True,       # let bass/beats modulate video modes
        "video_bass_boost": 0.3,      # up to +30% brightness on bass
        "beat_flash": 0.25,           # extra brightness on a detected beat
        "music_style": "pulse",       # pulse | spectrum
    },
    "outputs": {
        "wled": {
            "enabled": True,
            "host": "wled.local",
            "port": 4048,
            "leds": 0,                # 0 = same count as the layout
            "color_correction": [255, 176, 240],   # typical WS2812B white balance
        },
        "hue": {
            "enabled": False,
            "bridge": "",
            "app_key": "",
            "client_key": "",
            "entertainment_id": "",
            "max_rate": 25,
            "channel_map": {},        # optional {"<channel_id>": <led index>}
        },
        "spi": {
            "enabled": False,
            "device": "/dev/spidev0.0",
            "color_order": "GRB",
            "color_correction": [255, 176, 240],
        },
        "adalight": {
            "enabled": False,
            "port": "/dev/ttyUSB0",
            "baud": 115200,
        },
    },
    "web": {
        "host": "0.0.0.0",
        "port": 8080,
    },
}


def deep_merge(base: dict, patch: dict) -> dict:
    """Recursively merge ``patch`` into a copy of ``base``."""
    out = copy.deepcopy(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


class Config:
    """Thread-safe configuration store backed by a YAML file."""

    def __init__(self, path: str | Path | None = None, overrides: dict | None = None):
        self.path = Path(path) if path else None
        self._lock = threading.Lock()
        self._data = copy.deepcopy(DEFAULTS)
        self.version = 0
        if self.path and self.path.exists():
            with open(self.path, encoding="utf-8") as fh:
                loaded = yaml.safe_load(fh) or {}
            self._data = deep_merge(self._data, loaded)
        if overrides:
            self._data = deep_merge(self._data, overrides)

    def snapshot(self) -> dict:
        with self._lock:
            return copy.deepcopy(self._data)

    def get(self, *keys: str, default: Any = None) -> Any:
        with self._lock:
            node: Any = self._data
            for key in keys:
                if not isinstance(node, dict) or key not in node:
                    return default
                node = node[key]
            return copy.deepcopy(node)

    def update(self, patch: dict, save: bool = True) -> dict:
        with self._lock:
            self._data = deep_merge(self._data, patch)
            self.version += 1
            data = copy.deepcopy(self._data)
        if save:
            self.save(data)
        return data

    def save(self, data: dict | None = None) -> None:
        if not self.path:
            return
        data = data if data is not None else self.snapshot()
        tmp = self.path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            yaml.safe_dump(data, fh, sort_keys=False)
        tmp.replace(self.path)
