"""Synthetic tests for syncbox-ui against the fake HyperHDR (label SYN)."""
import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "installer" / "syncbox-ui"))
sys.path.insert(0, str(ROOT / "tools" / "tests"))


@pytest.fixture(scope="module")
def fake():
    import fake_hyperhdr
    httpd = fake_hyperhdr.serve(18090)
    os.environ["HYPERHDR_URL"] = "http://127.0.0.1:18090"
    yield fake_hyperhdr.STATE
    httpd.shutdown()


@pytest.fixture
def client(fake, tmp_path):
    os.environ["SYNCBOX_CONFIG"] = str(tmp_path / "syncbox.json")
    os.environ["SYNCBOX_DEFAULTS"] = str(ROOT / "installer" / "hyperhdr-defaults.json")
    import importlib
    import hyperhdr
    importlib.reload(hyperhdr)
    import app as ui
    importlib.reload(ui)
    return ui.app.test_client(), fake, ui


def test_redirects_to_wizard_first_boot(client):
    c, _, _ = client
    r = c.get("/")
    assert r.status_code == 302 and "/wizard" in r.headers["Location"]
    assert c.get("/wizard").status_code == 200


def test_layout_matches_reference_geometry(client):
    _, _, ui = client
    lay = ui.led_layout(4, 2, 4, 2)
    assert len(lay) == 12 and lay[0]["hmin"] == 0 and lay[0]["vmax"] == 1.0   # left edge, bottom
    assert lay[2]["vmin"] == 0 and lay[5]["hmax"] == 1.0                      # top edge
    s = ui.suggest_counts(55, 60, sides=3)
    assert s["bottom"] == 0 and 60 <= s["top"] <= 75 and 30 <= s["left"] <= 42


def test_wizard_pushes_config_and_finishes(client):
    c, fake, _ = client
    fake["requests"].clear()
    r = c.post("/api/wizard", json={"tv_inches": 55, "leds": {"top": 68, "right": 37, "bottom": 0, "left": 37}, "done": True})
    j = r.get_json()
    assert j["ok"] and j["leds"] == 142
    sections = [q["config"] for q in fake["requests"] if q.get("command") == "config"]
    assert any("leds" in s and len(s["leds"]) == 142 for s in sections)
    assert any("smoothing" in s for s in sections) and any("videoGrabber" in s for s in sections)
    assert c.get("/").status_code == 200   # wizard done -> main page


def test_mode_intensity_brightness_power(client):
    c, fake, _ = client
    c.post("/api/wizard", json={"leds": {"top": 8, "right": 4, "bottom": 0, "left": 4}, "done": True})
    fake["requests"].clear()
    assert c.post("/api/mode", json={"mode": "game"}).get_json()["state"]["mode"] == "game"
    sm = [q for q in fake["requests"] if q.get("command") == "config" and "smoothing" in q["config"]]
    assert sm and sm[-1]["config"]["smoothing"]["time_ms"] == 30
    adj = [q for q in fake["requests"] if q.get("command") == "adjustment"][-1]["adjustment"]
    assert adj["brightness"] == 90 and abs(adj["saturationGain"] - 1.2 * 1.2) < 1e-6
    c.post("/api/intensity", json={"intensity": "subtle"})
    adj = [q for q in fake["requests"] if q.get("command") == "adjustment"][-1]["adjustment"]
    assert adj["brightness"] == 54
    c.post("/api/mode", json={"mode": "music"})
    assert any(q.get("command") == "effect" for q in fake["requests"])
    assert c.post("/api/mode", json={"mode": "disco"}).status_code == 400
    c.post("/api/power", json={"on": False})
    assert fake["leds"] is False
    st = c.get("/api/state").get_json()
    assert st["online"] and st["hyperhdr"]["leds_enabled"] is False


def test_calibrate_and_offline(client):
    c, fake, _ = client
    assert c.post("/api/calibrate", json={"edge": "top"}).get_json()["ok"]
    assert [q for q in fake["requests"] if q.get("command") == "color"][-1]["color"] == [255, 0, 0]
    assert c.post("/api/calibrate", json={"stop": True}).get_json()["ok"]
    os.environ["HYPERHDR_URL"] = "http://127.0.0.1:1"
    import importlib
    import hyperhdr
    importlib.reload(hyperhdr)
    import app as ui
    importlib.reload(ui)
    st = ui.app.test_client().get("/api/state").get_json()
    assert st["online"] is False and "unreachable" in st["hyperhdr"]["error"]
    os.environ["HYPERHDR_URL"] = "http://127.0.0.1:18090"
