"""Audio analysis: bass / mid / treble levels and beat detection.

Runs a `sounddevice` input stream (PortAudio) in the background and keeps a
small dictionary of features that the engine reads every frame:

    level   0..1  overall loudness (auto-gain controlled)
    bass    0..1  20-200 Hz energy
    mid     0..1  200-2000 Hz energy
    treble  0..1  2-16 kHz energy
    beat    bool  True for the frame right after an onset in the bass band
    beat_t  float time.monotonic() of the last beat

The audio can come from a USB line-in adapter fed by the sound bar's 3.5 mm
out, from an optical->analog DAC, or simply from the HDMI capture card, which
exposes the HDMI audio as a USB microphone.
"""
from __future__ import annotations

import threading
import time
from collections import deque

import numpy as np

try:
    import sounddevice as sd
except Exception:  # pragma: no cover - PortAudio not installed
    sd = None

BANDS = {"bass": (20, 200), "mid": (200, 2000), "treble": (2000, 16000)}


class BandAnalyzer:
    """Pure-numpy feature extractor (separated from I/O so it can be unit tested)."""

    def __init__(self, samplerate: int, blocksize: int, sensitivity: float = 1.0):
        self.samplerate = samplerate
        self.blocksize = blocksize
        self.sensitivity = sensitivity
        self.window = np.hanning(blocksize).astype(np.float32)
        freqs = np.fft.rfftfreq(blocksize, 1.0 / samplerate)
        self.masks = {k: (freqs >= lo) & (freqs < hi) for k, (lo, hi) in BANDS.items()}
        self.peaks = {k: 1e-3 for k in BANDS}
        self.peak_level = 1e-3
        self.bass_history: deque[float] = deque(maxlen=max(8, int(samplerate / blocksize)))
        self.last_beat = 0.0
        self.features = {"level": 0.0, "bass": 0.0, "mid": 0.0, "treble": 0.0, "beat": False, "beat_t": 0.0}

    def analyze(self, mono: np.ndarray, now: float | None = None) -> dict:
        now = time.monotonic() if now is None else now
        if mono.shape[0] != self.blocksize:
            mono = np.resize(mono, self.blocksize)
        spec = np.abs(np.fft.rfft(mono * self.window))
        feats = {}
        for name, mask in self.masks.items():
            energy = float(spec[mask].mean()) if mask.any() else 0.0
            # slow-decay peak tracker acts as automatic gain control
            self.peaks[name] = max(self.peaks[name] * 0.995, energy, 1e-6)
            feats[name] = min(1.0, energy / self.peaks[name] * self.sensitivity)
        rms = float(np.sqrt(np.mean(mono * mono)))
        self.peak_level = max(self.peak_level * 0.995, rms, 1e-6)
        feats["level"] = min(1.0, rms / self.peak_level * self.sensitivity)

        # Beat: bass energy jumps above its recent average, with a refractory period
        raw_bass = float(spec[self.masks["bass"]].mean()) if self.masks["bass"].any() else 0.0
        avg = float(np.mean(self.bass_history)) if self.bass_history else raw_bass
        self.bass_history.append(raw_bass)
        beat = (
            raw_bass > avg * 1.35
            and raw_bass > 0.15 * self.peaks["bass"]
            and (now - self.last_beat) > 0.12
        )
        if beat:
            self.last_beat = now
        feats["beat"] = bool(beat)
        feats["beat_t"] = self.last_beat
        self.features = feats
        return feats


class AudioAnalyzer:
    """Background thread wrapper around BandAnalyzer + sounddevice."""

    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.samplerate = int(cfg.get("samplerate", 48000))
        self.channels = int(cfg.get("channels", 2))
        self.blocksize = int(cfg.get("blocksize", 1024))
        self.ms2109_fix = bool(cfg.get("ms2109_fix", False))
        self.analyzer = BandAnalyzer(
            self.samplerate // 2 if self.ms2109_fix else self.samplerate,
            self.blocksize,
            float(cfg.get("sensitivity", 1.0)),
        )
        self._lock = threading.Lock()
        self._features = dict(self.analyzer.features)
        self._beat_pending = False
        self.stream = None
        self.error: str | None = None

    def start(self) -> bool:
        if sd is None:
            self.error = "sounddevice/PortAudio not installed"
            return False
        try:
            self.stream = sd.InputStream(
                device=self.cfg.get("device"),
                channels=self.channels,
                samplerate=self.samplerate,
                blocksize=self.blocksize,
                dtype="float32",
                callback=self._callback,
            )
            self.stream.start()
            return True
        except Exception as exc:  # device missing, wrong rate, ...
            self.error = str(exc)
            self.stream = None
            return False

    def _callback(self, indata, frames, time_info, status):
        block = np.asarray(indata, dtype=np.float32)
        if self.ms2109_fix and self.channels == 1:
            # 96 kHz mono is really 48 kHz stereo interleaved L,R,L,R...
            block = block.reshape(-1, 2)
        mono = block.mean(axis=1) if block.ndim == 2 else block
        if mono.shape[0] != self.analyzer.blocksize:
            self.analyzer = BandAnalyzer(self.analyzer.samplerate, mono.shape[0], self.analyzer.sensitivity)
        feats = self.analyzer.analyze(mono)
        with self._lock:
            if feats["beat"]:
                self._beat_pending = True
            self._features = feats

    def snapshot(self) -> dict:
        """Return the latest features; a beat is reported exactly once."""
        with self._lock:
            feats = dict(self._features)
            feats["beat"] = self._beat_pending
            self._beat_pending = False
            return feats

    def set_sensitivity(self, value: float) -> None:
        self.analyzer.sensitivity = float(value)

    def stop(self) -> None:
        if self.stream is not None:
            try:
                self.stream.stop()
                self.stream.close()
            finally:
                self.stream = None


def hsv_to_rgb(h: np.ndarray, s: np.ndarray, v: np.ndarray) -> np.ndarray:
    """Vectorised HSV (0..1) -> RGB (0..255 float)."""
    h = np.mod(h, 1.0) * 6.0
    i = np.floor(h).astype(int)
    f = h - i
    p = v * (1 - s)
    q = v * (1 - s * f)
    t = v * (1 - s * (1 - f))
    i = i % 6
    r = np.choose(i, [v, q, p, p, t, v])
    g = np.choose(i, [t, v, v, q, p, p])
    b = np.choose(i, [p, p, t, v, v, q])
    return np.stack([r, g, b], axis=1) * 255.0


class MusicVisualizer:
    """Audio-only lighting used by the *music* mode and the audio fallback."""

    def __init__(self, n: int):
        self.n = n
        self.hue = 0.0
        self.env = 0.0
        self.flash = 0.0
        self.pos = np.linspace(0, 1, n, endpoint=False) if n else np.zeros(0)

    def render(self, feats: dict, dt: float, style: str = "pulse") -> np.ndarray:
        level = feats.get("bass", 0.0) * 0.7 + feats.get("level", 0.0) * 0.3
        # envelope follower: fast attack, slower release
        self.env += (level - self.env) * (0.6 if level > self.env else 0.15)
        self.flash = max(0.0, self.flash - dt * 4.0)
        if feats.get("beat"):
            self.flash = 1.0
        self.hue = (self.hue + dt * (0.02 + 0.1 * feats.get("treble", 0.0))) % 1.0

        if style == "spectrum":
            # strip position maps bass (start) -> treble (end), mirrored around the middle
            m = np.abs(self.pos - 0.5) * 2.0
            band = np.where(m < 0.33, feats.get("bass", 0.0), np.where(m < 0.66, feats.get("mid", 0.0), feats.get("treble", 0.0)))
            h = (self.hue + m * 0.4) % 1.0
            v = np.clip(band, 0, 1)
            s = np.full(self.n, 1.0)
        else:  # pulse
            h = (self.hue + self.pos * 0.15) % 1.0
            v = np.clip(0.08 + 0.92 * self.env + 0.5 * self.flash, 0, 1) * np.ones(self.n)
            s = np.full(self.n, 1.0 - 0.6 * self.flash)  # beats flash towards white
        return np.clip(hsv_to_rgb(h, s, v), 0, 255)
