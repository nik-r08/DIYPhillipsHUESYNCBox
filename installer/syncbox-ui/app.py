"""syncbox-ui: the phone-sized control page. Port 80. Talks to HyperHDR over JSON-RPC.

Pages:
  /            on/off, mode (Game/Video/Movie/Music), intensity, brightness, status
  /wizard      first boot: TV size -> LED counts -> layout -> calibration -> Hue
  /advanced    links to HyperHDR (8090), doctor output, update/rollback, persistence
API (JSON): /api/state, /api/power, /api/mode, /api/intensity, /api/brightness, /api/wizard, /api/calibrate
"""
from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template, request

import hyperhdr as H

CONFIG_PATH = Path(os.environ.get("SYNCBOX_CONFIG", "/etc/syncbox/syncbox.json"))
DEFAULTS_PATH = Path(os.environ.get("SYNCBOX_DEFAULTS", "/etc/syncbox/hyperhdr-defaults.json"))
PORT = int(os.environ.get("SYNCBOX_PORT", "80"))

app = Flask(__name__, template_folder=str(Path(__file__).parent / "templates"))
_lock = threading.Lock()


# ---------------------------------------------------------------- config
def load_state() -> dict:
    base = {"wizard_done": False, "tv_inches": 55, "mode": "video", "intensity": "high", "brightness": 90,
            "power": True, "hue_enabled": False, "leds": {"top": 68, "right": 37, "bottom": 0, "left": 37,
            "start": "bottom-left", "direction": "clockwise"}}
    try:
        base.update(json.loads(CONFIG_PATH.read_text()))
    except Exception:
        pass
    return base


def save_state(state: dict) -> None:
    with _lock:
        tmp = CONFIG_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, indent=1))
        tmp.replace(CONFIG_PATH)


def defaults() -> dict:
    try:
        return json.loads(DEFAULTS_PATH.read_text())
    except Exception:
        return {"modes": {}, "intensity": {}}


# ---------------------------------------------------------------- LED layout -> HyperHDR "leds" array
def led_layout(top: int, right: int, bottom: int, left: int, start="bottom-left", direction="clockwise", border=0.08):
    """Same geometry as reference/python-pipeline/syncbox/zones.py, emitted in HyperHDR's
    format: [{"hmin","hmax","vmin","vmax"}] in strip order, values 0..1."""
    def edge(e, n):
        out = []
        for i in range(n):
            a, b = i / n, (i + 1) / n
            if e == "top":      out.append((a, 0.0, b, border))
            elif e == "right":  out.append((1 - border, a, 1.0, b))
            elif e == "bottom": out.append((1 - b, 1 - border, 1 - a, 1.0))
            else:               out.append((0.0, 1 - b, border, 1 - a))
        return out
    segs = [("bottom-left", edge("left", left)), ("top-left", edge("top", top)),
            ("top-right", edge("right", right)), ("bottom-right", edge("bottom", bottom))]
    if direction == "counterclockwise":
        segs = [("bottom-left", segs[3][1][::-1]), ("bottom-right", segs[2][1][::-1]),
                ("top-right", segs[1][1][::-1]), ("top-left", segs[0][1][::-1])]
    k = [s[0] for s in segs].index(start)
    segs = segs[k:] + segs[:k]
    rects = [r for _, s in segs for r in s]
    return [{"hmin": round(x0, 4), "hmax": round(x1, 4), "vmin": round(y0, 4), "vmax": round(y1, 4)} for x0, y0, x1, y1 in rects]


def suggest_counts(tv_inches: int, density: int = 60, inset_cm: float = 5.0, sides: int = 3) -> dict:
    """16:9 panel; width = diag * 0.8716, height = diag * 0.4903 (inches). UNT until measured."""
    w_cm = tv_inches * 0.8716 * 2.54 - 2 * inset_cm
    h_cm = tv_inches * 0.4903 * 2.54 - 2 * inset_cm
    top = int(w_cm / 100 * density)
    side = int(h_cm / 100 * density)
    return {"top": top, "right": side, "bottom": top if sides == 4 else 0, "left": side}


# ---------------------------------------------------------------- applying modes
def apply_mode(state: dict) -> list[str]:
    """Push mode + intensity + brightness + power to HyperHDR. Returns a list of warnings."""
    d = defaults()
    warnings = []
    mode = d.get("modes", {}).get(state["mode"], {})
    inten = d.get("intensity", {}).get(state["intensity"], {"saturationGain": 1.0, "brightness_scale": 1.0, "time_scale": 1.0})
    bri = int(max(0, min(100, state["brightness"] * inten.get("brightness_scale", 1.0))))
    try:
        H.leds_on(bool(state.get("power", True)))
    except H.HyperHDRError as exc:
        return [str(exc)]
    if not state.get("power", True):
        return warnings
    try:
        if "effect" in mode:            # music mode: an audio-reactive effect on a higher priority than the grabber
            H.set_effect(mode["effect"], priority=100)
        else:
            H.clear(100)
            H.set_config("smoothing", {"time_ms": int(mode.get("time_ms", 120) * inten.get("time_scale", 1.0)),
                                       "updateFrequency": mode.get("updateFrequency", 50), "enable": True})
    except H.HyperHDRError as exc:
        warnings.append(f"smoothing/effect: {exc}")
    try:
        H.set_adjustment(brightness=bri, saturationGain=float(mode.get("saturationGain", 1.0)) * float(inten.get("saturationGain", 1.0)))
    except H.HyperHDRError as exc:
        warnings.append(f"adjustment: {exc}")
    return warnings


# ---------------------------------------------------------------- routes
@app.get("/")
def index():
    st = load_state()
    if not st.get("wizard_done"):
        return redirect("/wizard")
    return render_template("index.html", state=st)


@app.get("/wizard")
def wizard():
    return render_template("wizard.html", state=load_state())


@app.get("/advanced")
def advanced():
    return render_template("advanced.html", state=load_state(), host=request.host.split(":")[0])


@app.get("/api/state")
def api_state():
    st = load_state()
    try:
        sig = H.signal_state()
        st["hyperhdr"] = sig
        st["online"] = True
    except H.HyperHDRError as exc:
        st["hyperhdr"] = {"error": str(exc)}
        st["online"] = False
    return jsonify(st)


def _update(fields: dict):
    st = load_state()
    st.update(fields)
    save_state(st)
    return jsonify({"ok": True, "state": st, "warnings": apply_mode(st)})


@app.post("/api/power")
def api_power():
    return _update({"power": bool((request.get_json(silent=True) or {}).get("on", True))})


@app.post("/api/mode")
def api_mode():
    mode = (request.get_json(silent=True) or {}).get("mode")
    if mode not in ("game", "video", "movie", "music"):
        return jsonify({"error": "unknown mode"}), 400
    return _update({"mode": mode, "power": True})


@app.post("/api/intensity")
def api_intensity():
    inten = (request.get_json(silent=True) or {}).get("intensity")
    if inten not in ("subtle", "moderate", "high", "extreme"):
        return jsonify({"error": "unknown intensity"}), 400
    return _update({"intensity": inten})


@app.post("/api/brightness")
def api_brightness():
    b = (request.get_json(silent=True) or {}).get("brightness")
    try:
        b = int(b)
    except (TypeError, ValueError):
        return jsonify({"error": "brightness 0..100"}), 400
    return _update({"brightness": max(0, min(100, b))})


@app.get("/api/suggest")
def api_suggest():
    inches = int(request.args.get("inches", 55))
    sides = int(request.args.get("sides", 3))
    density = int(request.args.get("density", 60))
    return jsonify(suggest_counts(inches, density, sides=sides))


@app.post("/api/wizard")
def api_wizard():
    body = request.get_json(force=True, silent=True) or {}
    leds = body.get("leds") or {}
    try:
        counts = {k: int(leds.get(k, 0)) for k in ("top", "right", "bottom", "left")}
    except (TypeError, ValueError):
        return jsonify({"error": "led counts must be integers"}), 400
    layout = led_layout(**counts, start=leds.get("start", "bottom-left"), direction=leds.get("direction", "clockwise"))
    warnings = []
    d = defaults()
    try:
        H.set_config("leds", layout)
        for section in ("videoGrabber", "blackborderdetector", "smoothing", "device"):
            if section in d:
                try:
                    H.set_config(section, d[section])
                except H.HyperHDRError as exc:
                    warnings.append(f"{section}: {exc}")
    except H.HyperHDRError as exc:
        warnings.append(f"leds: {exc}")
    st = load_state()
    st.update({"leds": {**counts, "start": leds.get("start", "bottom-left"), "direction": leds.get("direction", "clockwise")},
               "tv_inches": int(body.get("tv_inches", st.get("tv_inches", 55))), "wizard_done": bool(body.get("done", False))})
    save_state(st)
    return jsonify({"ok": True, "leds": len(layout), "warnings": warnings})


@app.post("/api/calibrate")
def api_calibrate():
    """Light each edge a different colour for 20 s: top red, right green, bottom blue, left yellow."""
    body = request.get_json(silent=True) or {}
    if body.get("stop"):
        try:
            H.clear(50)
        except H.HyperHDRError as exc:
            return jsonify({"error": str(exc)}), 502
        return jsonify({"ok": True})
    colour = {"top": [255, 0, 0], "right": [0, 255, 0], "bottom": [0, 0, 255], "left": [255, 200, 0]}.get(body.get("edge", "top"))
    try:
        H.set_color(colour, priority=50, duration=20000)
    except H.HyperHDRError as exc:
        return jsonify({"error": str(exc)}), 502
    return jsonify({"ok": True, "note": "whole strip shows one colour per step; confirm which physical edge lights for each step"})


@app.post("/api/system/<action>")
def api_system(action):
    cmds = {"update": ["sudo", "-n", "/usr/local/bin/syncbox-update"], "rollback": ["sudo", "-n", "/usr/local/bin/syncbox-rollback"],
            "doctor": ["/usr/local/bin/syncbox-doctor"], "reboot": ["sudo", "-n", "reboot"],
            "persist-status": ["sudo", "-n", "/usr/local/sbin/syncbox-persist", "status"]}
    if action not in cmds:
        return jsonify({"error": "unknown action"}), 400
    try:
        out = subprocess.run(cmds[action], capture_output=True, text=True, timeout=600)
        return jsonify({"rc": out.returncode, "out": (out.stdout + out.stderr)[-4000:]})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


def _watchdog_ping():
    """Tell systemd we are alive (WatchdogSec=60 in the unit)."""
    try:
        import socket
        addr = os.environ.get("NOTIFY_SOCKET")
        if not addr:
            return
        s = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        while True:
            s.sendto(b"WATCHDOG=1", addr)
            time.sleep(20)
    except Exception:
        pass


if __name__ == "__main__":
    threading.Thread(target=_watchdog_ping, daemon=True).start()
    st = load_state()
    if st.get("wizard_done"):
        threading.Thread(target=lambda: (time.sleep(5), apply_mode(st)), daemon=True).start()   # re-apply after boot
    app.run(host="0.0.0.0", port=PORT, threaded=True)
