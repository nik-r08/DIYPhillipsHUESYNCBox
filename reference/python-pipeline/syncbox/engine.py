"""The main loop: capture -> process -> outputs, with modes and fallbacks."""
from __future__ import annotations

import logging
import threading
import time

import numpy as np

from .audio import AudioAnalyzer, MusicVisualizer
from .capture import Capture
from .config import Config
from .outputs import MemoryOutput, build_outputs
from .processor import INTENSITY_PRESETS, Smoother, apply_gamma
from .zones import layout_with_edges_from_config

log = logging.getLogger("syncbox")
VIDEO_MODES = ("game", "video", "movie")
CALIBRATION_COLORS = {"top": (255, 0, 0), "right": (0, 255, 0), "bottom": (0, 0, 255), "left": (255, 200, 0)}


class Engine:
    def __init__(self, config: Config, outputs=None, capture: Capture | None = None, audio=None, enable_audio: bool = True):
        self.config = config
        cfg = config.snapshot()
        self._leds_cfg = dict(cfg["leds"])
        self._outputs_cfg = dict(cfg["outputs"])
        self._capture_cfg = dict(cfg["capture"])
        self._audio_cfg = dict(cfg["audio"])
        self.rects, self.edges = layout_with_edges_from_config(cfg["leds"])
        self.n = len(self.rects)
        from .processor import VideoProcessor  # local import keeps module load light
        self.processor = VideoProcessor(self.rects, cfg["capture"].get("sample_width", 256))
        self.music = MusicVisualizer(self.n)
        self.aux_smoother = Smoother(self.n)          # for static / music colours
        self.capture = capture or Capture(cfg["capture"])
        self._external_outputs = outputs is not None
        self.outputs = outputs if outputs is not None else self._safe_build_outputs(cfg)
        self.preview = MemoryOutput()
        self.audio = audio
        self._enable_audio = enable_audio
        if self.audio is None and enable_audio and cfg["audio"].get("enabled"):
            self.audio = AudioAnalyzer(cfg["audio"])
            if not self.audio.start():
                log.warning("audio disabled: %s", self.audio.error)
        self._stop = threading.Event()
        self._last_seq = -1
        self._black_since: float | None = None
        self._flash = 0.0
        self._last_beat_t = 0.0
        self.fps = 0.0
        self.status: dict = {}
        self.status_lock = threading.Lock()
        self.last_colors = np.zeros((self.n, 3), dtype=np.uint8)

    # -- helpers ----------------------------------------------------------------
    def _safe_build_outputs(self, cfg):
        outs = []
        try:
            outs = build_outputs(cfg, self.rects)
        except Exception as exc:
            log.error("output init failed: %s", exc)
        return outs

    def _apply_config_changes(self, cfg: dict) -> None:
        if cfg["leds"] != self._leds_cfg:
            self._leds_cfg = dict(cfg["leds"])
            self.rects, self.edges = layout_with_edges_from_config(cfg["leds"])
            self.n = len(self.rects)
            from .processor import VideoProcessor
            self.processor = VideoProcessor(self.rects, cfg["capture"].get("sample_width", 256))
            self.music = MusicVisualizer(self.n)
            self.aux_smoother = Smoother(self.n)
            self._outputs_cfg = None  # force output rebuild (Hue mapping depends on layout)
        if not self._external_outputs and cfg["outputs"] != self._outputs_cfg:
            self._outputs_cfg = dict(cfg["outputs"])
            for o in self.outputs:
                try:
                    o.close()
                except Exception:
                    pass
            self.outputs = self._safe_build_outputs(cfg)
        if cfg["capture"] != self._capture_cfg and not isinstance(self.capture, _StaticCapture):
            self._capture_cfg = dict(cfg["capture"])
            self.capture.stop()
            self.capture = Capture(cfg["capture"])
            self.capture.start()
        if cfg["audio"] != self._audio_cfg and self._enable_audio:
            self._audio_cfg = dict(cfg["audio"])
            if self.audio is not None:
                self.audio.stop()
                self.audio = None
            if cfg["audio"].get("enabled"):
                self.audio = AudioAnalyzer(cfg["audio"])
                if not self.audio.start():
                    log.warning("audio disabled: %s", self.audio.error)

    def _finish(self, colors_float: np.ndarray, dt: float, tau: float, brightness: float, gamma: float) -> np.ndarray:
        c = self.aux_smoother.step(np.clip(colors_float, 0, 255).astype(np.float32), dt, tau, tau)
        out = apply_gamma(c / 255.0, gamma) * brightness
        return (np.clip(out, 0, 1) * 255.0 + 0.5).astype(np.uint8)

    # -- one iteration ------------------------------------------------------------
    def step(self, now: float, dt: float, cfg: dict) -> np.ndarray:
        proc, cap_cfg, fb, audio_cfg = cfg["processing"], cfg["capture"], cfg["fallback"], cfg["audio"]
        mode = proc.get("mode", "video")
        preset = INTENSITY_PRESETS.get(proc.get("intensity", "high"), INTENSITY_PRESETS["high"])
        brightness = float(proc.get("brightness", 1.0)) * preset["brightness"]
        gamma = float(proc.get("gamma", 2.2))

        # ---- capture / signal detection
        frame, seq, ts = self.capture.latest()
        if frame is not None and seq != self._last_seq:
            self._last_seq = seq
            raw = self.processor.extract(frame, bool(cap_cfg.get("black_bar_detection", True)))
            if float(raw.max()) < 3.0:
                self._black_since = self._black_since or now
            else:
                self._black_since = None
        raw = self.processor.last_raw
        fresh = frame is not None and (now - ts) < float(cap_cfg.get("signal_timeout", 3.0))
        black_too_long = self._black_since is not None and (now - self._black_since) > float(cap_cfg.get("black_timeout", 30.0))
        signal = fresh and not black_too_long

        # ---- audio features
        feats = self.audio.snapshot() if self.audio is not None else {}
        self._flash = max(0.0, self._flash - dt * 6.0)
        if feats.get("beat"):
            self._flash = 1.0
        audio_gain = 1.0
        if feats and audio_cfg.get("react_in_video", True):
            audio_gain = 1.0 + float(audio_cfg.get("video_bass_boost", 0.3)) * feats.get("bass", 0.0) \
                + float(audio_cfg.get("beat_flash", 0.25)) * self._flash

        # ---- pick what to show
        effective = mode
        if mode in VIDEO_MODES and not signal:
            effective = {"static": "fallback-static", "off": "off", "music": "music"}.get(fb.get("when_no_signal", "static"), "fallback-static")

        if effective in VIDEO_MODES:
            params = proc.get("modes", {}).get(effective, {"tau_up": 0.08, "tau_down": 0.2})
            colors = self.processor.process(raw, dt, proc, params, audio_gain)
        elif effective == "music":
            music_colors = self.music.render(feats, dt, audio_cfg.get("music_style", "pulse"))
            colors = self._finish(music_colors, dt, 0.03, brightness, gamma)
        elif effective == "calibrate":
            # top=red, right=green, bottom=blue, left=yellow; first 3 LEDs white
            cal = np.array([CALIBRATION_COLORS[e] for e in self.edges], dtype=np.float32).reshape(-1, 3)
            cal[:3] = 255
            colors = self._finish(cal, dt, 0.05, brightness, gamma)
        elif effective == "static":
            colors = self._finish(np.tile(np.asarray(proc.get("static_color", [255, 140, 40]), dtype=np.float32), (self.n, 1)), dt, 0.3, brightness, gamma)
        elif effective == "fallback-static":
            colors = self._finish(np.tile(np.asarray(fb.get("color", [40, 20, 80]), dtype=np.float32), (self.n, 1)), dt, 0.5, brightness, gamma)
        else:  # off
            colors = self._finish(np.zeros((self.n, 3), dtype=np.float32), dt, 0.5, brightness, gamma)

        # ---- send
        for out in self.outputs:
            try:
                out.send(colors)
            except Exception as exc:
                log.debug("output %s failed: %s", out.name, exc)
        self.preview.send(colors)
        self.last_colors = colors

        with self.status_lock:
            self.status = {
                "mode": mode,
                "effective_mode": effective,
                "signal": bool(signal),
                "capture_fps": round(self.capture.fps, 1),
                "capture_error": getattr(self.capture, "error", None),
                "frame_size": list(getattr(self.capture, "actual_size", (0, 0))),
                "engine_fps": round(self.fps, 1),
                "leds": int(self.n),
                "scene_luma": round(float(self.processor.scene_luma), 3),
                "content_rect": (
                    [self.processor.bars.current.x0, self.processor.bars.current.y0, self.processor.bars.current.x1, self.processor.bars.current.y1]
                    if self.processor.bars.current else None
                ),
                "outputs": {o.name: getattr(o, "error", None) for o in self.outputs},
                "audio": {**{k: (round(v, 3) if isinstance(v, float) else v) for k, v in feats.items()},
                          "error": getattr(self.audio, "error", None) if self.audio else "disabled"},
            }
        return colors

    # -- main loop ----------------------------------------------------------------
    def run(self, duration: float | None = None) -> None:
        if not self.capture.is_alive():
            self.capture.start()
        cfg = self.config.snapshot()
        version = self.config.version
        t_prev = time.monotonic()
        t_end = t_prev + duration if duration else None
        t_fps, n = t_prev, 0
        while not self._stop.is_set():
            now = time.monotonic()
            if self.config.version != version:
                cfg = self.config.snapshot()
                version = self.config.version
                self._apply_config_changes(cfg)
            dt = now - t_prev
            t_prev = now
            try:
                self.step(now, dt, cfg)
            except Exception:
                log.exception("engine step failed")
            n += 1
            if now - t_fps >= 1.0:
                self.fps = n / (now - t_fps)
                t_fps, n = now, 0
            if t_end and now >= t_end:
                break
            period = 1.0 / max(float(cfg.get("target_fps", 30)), 1.0)
            sleep = period - (time.monotonic() - now)
            if sleep > 0:
                time.sleep(sleep)
        self.shutdown()

    def stop(self) -> None:
        self._stop.set()

    def shutdown(self) -> None:
        self.capture.stop()
        if self.audio is not None:
            self.audio.stop()
        for o in self.outputs:
            try:
                o.close()
            except Exception:
                pass

    def get_status(self) -> dict:
        with self.status_lock:
            return dict(self.status)


class _StaticCapture:
    """Marker base so tests can inject a fake capture; see tests/."""
