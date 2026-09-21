import numpy as np
from syncbox.processor import (
    BlackBarDetector,
    Smoother,
    VideoProcessor,
    adjust_saturation,
    apply_black_threshold,
    resample_strip,
    spatial_blur,
)
from syncbox.zones import build_layout


def test_black_bars_letterbox_detected_and_held():
    d = BlackBarDetector(stable_frames=3)
    h, w = 72, 128
    luma = np.zeros((h, w), dtype=np.float32)
    luma[9:63, :] = 120.0            # 12.5% bars top and bottom
    for _ in range(2):
        rect = d.update(luma)
        assert (rect.y0, rect.y1) == (0, h)   # not yet stable
    rect = d.update(luma)
    assert (rect.x0, rect.y0, rect.x1, rect.y1) == (0, 9, w, 63)


def test_black_bars_ignore_dark_scene_and_asymmetric():
    d = BlackBarDetector(stable_frames=1)
    h, w = 72, 128
    dark = np.full((h, w), 5.0, dtype=np.float32)
    r = d.update(dark)
    assert (r.x0, r.y0, r.x1, r.y1) == (0, 0, w, h)
    asym = np.zeros((h, w), dtype=np.float32)
    asym[20:, :] = 100.0
    r = d.update(asym)
    assert (r.y0, r.y1) == (0, h)


def test_smoother_asymmetric():
    s = Smoother(1)
    up = s.step(np.array([[255, 255, 255]], dtype=np.float32), 0.05, tau_up=0.02, tau_down=0.5)
    assert up[0, 0] > 200
    down = s.step(np.zeros((1, 3), dtype=np.float32), 0.05, tau_up=0.02, tau_down=0.5)
    assert down[0, 0] > 150          # slow release


def test_black_threshold_and_saturation():
    c = np.array([[10, 10, 10], [255, 0, 0], [128, 128, 128]], dtype=np.float32)
    t = apply_black_threshold(c, 12)
    assert t[0].max() == 0 and t[1][0] == 255
    s = adjust_saturation(np.array([[200, 100, 100]], dtype=np.float32), 2.0)
    assert s[0][0] > 200 and s[0][1] < 100


def test_spatial_blur_and_resample():
    c = np.zeros((5, 3), dtype=np.float32)
    c[2] = 100
    b = spatial_blur(c, 1)
    assert b[1][0] == 25 and b[2][0] == 50 and b[3][0] == 25
    r = resample_strip(np.array([[0, 0, 0], [100, 100, 100]], dtype=np.float32), 3)
    assert np.allclose(r[1], [50, 50, 50])


def test_video_processor_end_to_end():
    rects = build_layout(8, 4, 8, 4, border=0.1)
    vp = VideoProcessor(rects, sample_width=64)
    frame = np.zeros((90, 160, 3), dtype=np.uint8)
    frame[:, :80] = (255, 0, 0)     # BGR: left half blue, right half red
    frame[:, 80:] = (0, 0, 255)
    raw = vp.extract(frame, black_bars=False)
    assert raw.shape == (24, 3)
    proc = {"intensity": "high", "brightness": 1.0, "saturation": 1.0, "gamma": 1.0, "black_threshold": 0,
            "content_brightness": False, "spatial_smoothing": 0}
    out = None
    for _ in range(50):
        out = vp.process(raw, 1 / 30, proc, {"tau_up": 0.01, "tau_down": 0.01})
    assert out.dtype == np.uint8
    # left edge LEDs (indices 0..3) blue, right edge (12..15) red
    assert out[0][2] > 200 and out[0][0] < 40
    assert out[12][0] > 200 and out[12][2] < 40
