import numpy as np
from syncbox.audio import BandAnalyzer, MusicVisualizer


def test_bands_respond_to_frequency():
    sr, n = 48000, 1024
    a = BandAnalyzer(sr, n)
    t = np.arange(n) / sr
    bass = np.sin(2 * np.pi * 60 * t).astype(np.float32)
    treble = np.sin(2 * np.pi * 8000 * t).astype(np.float32)
    for _ in range(5):
        f = a.analyze(bass, now=0.0)
    assert f["bass"] > 0.9 and f["treble"] < 0.3
    for _ in range(5):
        f = a.analyze(treble, now=1.0)
    assert f["treble"] > 0.9


def test_beat_detected_on_bass_onset():
    sr, n = 48000, 1024
    a = BandAnalyzer(sr, n)
    t = np.arange(n) / sr
    quiet = (0.05 * np.sin(2 * np.pi * 60 * t)).astype(np.float32)
    loud = np.sin(2 * np.pi * 60 * t).astype(np.float32)
    now = 0.0
    for _ in range(20):
        now += n / sr
        a.analyze(quiet, now=now)
    f = a.analyze(loud, now=now + n / sr)
    assert f["beat"] is True


def test_music_visualizer_shapes():
    m = MusicVisualizer(30)
    out = m.render({"bass": 0.8, "level": 0.5, "treble": 0.2, "beat": True}, 1 / 30, "pulse")
    assert out.shape == (30, 3) and out.max() <= 255 and out.max() > 100
    out = m.render({"bass": 0.8, "mid": 0.5, "treble": 0.2, "beat": False}, 1 / 30, "spectrum")
    assert out.shape == (30, 3)
