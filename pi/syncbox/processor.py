"""Colour processing pipeline: frame -> per-LED colours.

Pipeline order (all vectorised with numpy):

1. crop black bars (letterbox / pillarbox), shrink frame to the analysis size
2. mean colour per LED zone (summed-area table)
3. black threshold  -> kills noise "glow" in dark scenes
4. saturation boost
5. content brightness -> dim scenes stay dim, bright scenes pop
6. temporal smoothing -> asymmetric exponential filter (fast attack, slow decay)
7. spatial smoothing  -> blur between neighbouring LEDs
8. gamma              -> perceptual brightness curve
9. global brightness, clip, uint8
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .zones import ZoneSampler

try:  # OpenCV is optional for the pure-numpy paths (tests, non-Pi hosts)
    import cv2
except Exception:  # pragma: no cover - depends on environment
    cv2 = None

INTENSITY_PRESETS = {
    # multipliers applied on top of the user's own settings
    "subtle":   {"saturation": 0.9, "brightness": 0.6, "tau": 2.0, "black": 1.5},
    "moderate": {"saturation": 1.0, "brightness": 0.8, "tau": 1.3, "black": 1.0},
    "high":     {"saturation": 1.2, "brightness": 1.0, "tau": 1.0, "black": 1.0},
    "extreme":  {"saturation": 1.5, "brightness": 1.0, "tau": 0.5, "black": 0.5},
}


def resize_area(frame: np.ndarray, width: int, height: int) -> np.ndarray:
    """Shrink a frame with area averaging (OpenCV if present, numpy fallback)."""
    if frame.shape[0] == height and frame.shape[1] == width:
        return frame
    if cv2 is not None:
        return cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)
    # numpy fallback: nearest-neighbour block sampling
    ys = (np.arange(height) * frame.shape[0] / height).astype(int)
    xs = (np.arange(width) * frame.shape[1] / width).astype(int)
    return frame[ys][:, xs]


def luminance(rgb: np.ndarray) -> np.ndarray:
    return 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]


@dataclass
class ContentRect:
    x0: int
    y0: int
    x1: int
    y1: int


class BlackBarDetector:
    """Find the non-black picture area and hold it steady across frames."""

    def __init__(self, threshold: float = 18.0, max_crop: float = 0.3, stable_frames: int = 15):
        self.threshold = threshold
        self.max_crop = max_crop
        self.stable_frames = stable_frames
        self.current: ContentRect | None = None
        self._candidate: tuple[int, int, int, int] | None = None
        self._count = 0

    def detect(self, luma: np.ndarray) -> tuple[int, int, int, int]:
        h, w = luma.shape
        rows = luma.mean(axis=1) > self.threshold
        cols = luma.mean(axis=0) > self.threshold
        if not rows.any() or not cols.any():
            return (0, 0, w, h)          # whole frame dark: don't crop
        r = np.flatnonzero(rows)
        c = np.flatnonzero(cols)
        y0, y1 = int(r[0]), int(r[-1]) + 1
        x0, x1 = int(c[0]), int(c[-1]) + 1
        # Never crop more than max_crop on any side (a dark scene is not a bar)
        if y0 > h * self.max_crop or (h - y1) > h * self.max_crop:
            y0, y1 = 0, h
        if x0 > w * self.max_crop or (w - x1) > w * self.max_crop:
            x0, x1 = 0, w
        # Only trust symmetric bars (real letterbox/pillarbox are symmetric)
        if abs(y0 - (h - y1)) > max(2, h * 0.02):
            y0, y1 = 0, h
        if abs(x0 - (w - x1)) > max(2, w * 0.02):
            x0, x1 = 0, w
        return (x0, y0, x1, y1)

    def update(self, luma: np.ndarray) -> ContentRect:
        h, w = luma.shape
        if self.current is None:
            self.current = ContentRect(0, 0, w, h)
        rect = self.detect(luma)
        if rect == self._candidate:
            self._count += 1
        else:
            self._candidate, self._count = rect, 1
        if self._count >= self.stable_frames:
            self.current = ContentRect(*rect)
        return self.current


class Smoother:
    """Per-LED asymmetric exponential smoothing, frame-rate independent."""

    def __init__(self, n: int):
        self.state = np.zeros((n, 3), dtype=np.float32)

    def step(self, target: np.ndarray, dt: float, tau_up: float, tau_down: float) -> np.ndarray:
        dt = max(dt, 1e-4)
        a_up = 1.0 - math.exp(-dt / max(tau_up, 1e-4))
        a_down = 1.0 - math.exp(-dt / max(tau_down, 1e-4))
        rising = target > self.state
        alpha = np.where(rising, a_up, a_down).astype(np.float32)
        self.state += alpha * (target - self.state)
        return self.state


def spatial_blur(colors: np.ndarray, passes: int) -> np.ndarray:
    """Blur along the strip ([1,2,1]/4 kernel) with edge clamping."""
    out = colors
    for _ in range(int(passes)):
        left = np.concatenate([out[:1], out[:-1]], axis=0)
        right = np.concatenate([out[1:], out[-1:]], axis=0)
        out = 0.25 * left + 0.5 * out + 0.25 * right
    return out


def adjust_saturation(rgb: np.ndarray, factor: float) -> np.ndarray:
    if factor == 1.0:
        return rgb
    gray = luminance(rgb)[:, None]
    return gray + (rgb - gray) * factor


def apply_black_threshold(rgb: np.ndarray, threshold: float) -> np.ndarray:
    """Values below ``threshold`` fade to zero; above are re-stretched to 0..255."""
    if threshold <= 0:
        return rgb
    return np.clip((rgb - threshold) * (255.0 / (255.0 - threshold)), 0, 255)


def apply_gamma(rgb01: np.ndarray, gamma: float) -> np.ndarray:
    if gamma == 1.0:
        return rgb01
    return np.power(np.clip(rgb01, 0, 1), gamma)


def resample_strip(colors: np.ndarray, n_out: int) -> np.ndarray:
    """Linearly resample an (N,3) strip to (n_out,3) - lets an output with a
    different LED count follow the same layout."""
    n_in = colors.shape[0]
    if n_out == n_in or n_in == 0:
        return colors
    src = np.linspace(0, n_in - 1, n_out)
    lo = np.floor(src).astype(int)
    hi = np.minimum(lo + 1, n_in - 1)
    frac = (src - lo)[:, None]
    return colors[lo] * (1 - frac) + colors[hi] * frac


class VideoProcessor:
    """Turns captured frames into smoothed, gamma-corrected LED colours."""

    def __init__(self, rects: np.ndarray, sample_width: int = 256):
        self.rects = rects
        self.n = len(rects)
        self.sample_w = int(sample_width)
        self.sample_h = max(int(round(self.sample_w * 9 / 16)), 8)
        self.sampler = ZoneSampler(rects, self.sample_w, self.sample_h)
        self.bars = BlackBarDetector()
        self.smoother = Smoother(self.n)
        self.scene_luma = 0.5      # smoothed 0..1 scene brightness
        self.last_raw = np.zeros((self.n, 3), dtype=np.float32)

    # -- stage 1: frame -> raw zone colours (0..255 float) ------------------
    def extract(self, frame_bgr: np.ndarray, black_bars: bool = True) -> np.ndarray:
        # Work on a small copy first: cheap luma analysis for bar detection.
        small = resize_area(frame_bgr, self.sample_w, self.sample_h)
        luma = luminance(small[..., ::-1].astype(np.float32))
        if black_bars:
            rect = self.bars.update(luma)
            if (rect.x0, rect.y0, rect.x1, rect.y1) != (0, 0, self.sample_w, self.sample_h):
                # crop the ORIGINAL frame at the same proportions, then resize again
                h, w = frame_bgr.shape[:2]
                fy0 = rect.y0 * h // self.sample_h
                fy1 = int(math.ceil(rect.y1 * h / self.sample_h))
                fx0 = rect.x0 * w // self.sample_w
                fx1 = int(math.ceil(rect.x1 * w / self.sample_w))
                cropped = frame_bgr[fy0:fy1, fx0:fx1]
                small = resize_area(cropped, self.sample_w, self.sample_h)
                luma = luminance(small[..., ::-1].astype(np.float32))
        rgb = np.ascontiguousarray(small[..., ::-1])  # BGR -> RGB
        self.last_raw = self.sampler.sample(rgb)
        # scene luminance, lightly smoothed (used for content brightness)
        frame_luma = float(luma.mean()) / 255.0
        self.scene_luma += 0.1 * (frame_luma - self.scene_luma)
        return self.last_raw

    # -- stage 2: raw colours -> output colours -------------------------------
    def process(
        self,
        raw: np.ndarray,
        dt: float,
        proc: dict,
        mode_params: dict,
        audio_gain: float = 1.0,
    ) -> np.ndarray:
        preset = INTENSITY_PRESETS.get(proc.get("intensity", "high"), INTENSITY_PRESETS["high"])
        black = float(proc.get("black_threshold", 12)) * preset["black"]
        sat = float(proc.get("saturation", 1.0)) * preset["saturation"]
        bri = float(proc.get("brightness", 1.0)) * preset["brightness"] * audio_gain
        gamma = float(proc.get("gamma", 2.2))
        tau_up = float(mode_params.get("tau_up", 0.08)) * preset["tau"]
        tau_down = float(mode_params.get("tau_down", 0.2)) * preset["tau"]

        c = apply_black_threshold(raw, black)
        c = adjust_saturation(c, sat)
        if proc.get("content_brightness", True):
            # 0.35 .. 1.0 depending on how bright the scene is
            c = c * (0.35 + 0.65 * min(1.0, self.scene_luma * 2.0))
        c = np.clip(c, 0, 255)
        c = self.smoother.step(c.astype(np.float32), dt, tau_up, tau_down)
        c = spatial_blur(c, int(proc.get("spatial_smoothing", 0)))
        out = apply_gamma(c / 255.0, gamma) * bri
        return (np.clip(out, 0, 1) * 255.0 + 0.5).astype(np.uint8)

    def reset(self) -> None:
        self.smoother = Smoother(self.n)


def apply_color_correction(colors_u8: np.ndarray, correction) -> np.ndarray:
    """Per-channel white balance for a specific strip type (e.g. [255,176,240])."""
    if not correction:
        return colors_u8
    corr = np.asarray(correction, dtype=np.float32) / 255.0
    return (colors_u8.astype(np.float32) * corr + 0.5).astype(np.uint8)
