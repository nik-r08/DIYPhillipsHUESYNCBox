import threading
import time

from syncbox.config import Config
from syncbox.engine import Engine
from syncbox.outputs import MemoryOutput
from syncbox.web import create_app


def make_engine(tmp_path, **overrides):
    cfg = Config(tmp_path / "config.yaml", {
        "capture": {"device": "synthetic", "width": 160, "height": 90, "fps": 30, "sample_width": 64},
        "leds": {"top": 8, "right": 4, "bottom": 8, "left": 4},
        "outputs": {"wled": {"enabled": False}},
        "audio": {"enabled": False},
        **overrides,
    })
    mem = MemoryOutput()
    return Engine(cfg, outputs=[mem], enable_audio=False), mem


def test_engine_runs_synthetic_source(tmp_path):
    engine, mem = make_engine(tmp_path)
    engine.run(duration=0.8)
    assert mem.count > 5
    assert mem.last.shape == (24, 3)
    assert mem.last.max() > 50
    st = engine.get_status()
    assert st["signal"] is True and st["effective_mode"] == "video"


def test_fallback_when_no_signal(tmp_path):
    engine, mem = make_engine(tmp_path, capture={"device": "synthetic", "signal_timeout": 0.0})
    engine.run(duration=0.5)
    st = engine.get_status()
    assert st["signal"] is False and st["effective_mode"] == "fallback-static"
    assert mem.last.max() > 0


def test_web_api_roundtrip(tmp_path):
    engine, _mem = make_engine(tmp_path)
    app = create_app(engine)
    c = app.test_client()
    t = threading.Thread(target=engine.run, kwargs={"duration": 1.0}, daemon=True)
    t.start()
    time.sleep(0.3)
    assert c.get("/").status_code == 200
    r = c.post("/api/config", json={"processing": {"brightness": 0.42}})
    assert r.status_code == 200 and r.get_json()["processing"]["brightness"] == 0.42
    r = c.post("/api/mode", json={"mode": "movie"})
    assert r.get_json()["mode"] == "movie"
    assert c.post("/api/mode", json={"mode": "nope"}).status_code == 400
    r = c.get("/api/preview").get_json()
    assert len(r["colors"]) == 24 and r["colors"][0].startswith("#")
    assert "engine_fps" in c.get("/api/status").get_json()
    t.join()
    assert (tmp_path / "config.yaml").exists()
    reloaded = Config(tmp_path / "config.yaml")
    assert reloaded.get("processing", "mode") == "movie"


def test_layout_change_rebuilds_processor(tmp_path):
    engine, mem = make_engine(tmp_path)
    t = threading.Thread(target=engine.run, kwargs={"duration": 1.0}, daemon=True)
    t.start()
    time.sleep(0.3)
    engine.config.update({"leds": {"top": 10, "bottom": 10}})
    t.join()
    assert mem.last.shape == (28, 3)


def test_calibrate_mode_colours_edges(tmp_path):
    engine, mem = make_engine(tmp_path, processing={"mode": "calibrate", "gamma": 1.0, "brightness": 1.0, "intensity": "high"})
    engine.run(duration=0.6)
    c = mem.last
    assert c[:3].min() > 200                     # start marker is white
    assert c[3][0] > 200 and c[3][1] > 150 and c[3][2] < 30   # left edge -> yellow
    assert c[4][0] > 200 and c[4][2] < 30       # top edge -> red
    assert c[12][1] > 200 and c[12][0] < 30     # right edge -> green
    assert c[16][2] > 200 and c[16][0] < 30     # bottom edge -> blue
