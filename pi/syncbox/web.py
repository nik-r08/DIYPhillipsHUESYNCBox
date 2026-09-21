"""Flask web UI + JSON API for configuration and live status."""
from __future__ import annotations

from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from . import hue_pairing

STATIC_DIR = Path(__file__).parent / "static"


def create_app(engine) -> Flask:
    app = Flask("syncbox", static_folder=str(STATIC_DIR), static_url_path="/static")

    @app.get("/")
    def index():
        return send_from_directory(STATIC_DIR, "index.html")

    @app.get("/api/status")
    def status():
        return jsonify(engine.get_status())

    @app.get("/api/config")
    def get_config():
        return jsonify(engine.config.snapshot())

    @app.post("/api/config")
    def post_config():
        patch = request.get_json(force=True, silent=True) or {}
        if not isinstance(patch, dict):
            return jsonify({"error": "expected a JSON object"}), 400
        return jsonify(engine.config.update(patch))

    @app.post("/api/mode")
    def set_mode():
        body = request.get_json(force=True, silent=True) or {}
        mode = body.get("mode")
        if mode not in ("game", "video", "movie", "music", "static", "calibrate"):
            return jsonify({"error": "unknown mode"}), 400
        engine.config.update({"processing": {"mode": mode}})
        return jsonify({"mode": mode})

    @app.get("/api/preview")
    def preview():
        colors = engine.preview.last
        hexes = [] if colors is None else ["#%02x%02x%02x" % tuple(int(v) for v in c) for c in colors]
        leds = engine.config.get("leds")
        return jsonify({"colors": hexes, "layout": leds})

    @app.post("/api/hue/pair")
    def hue_pair():
        body = request.get_json(force=True, silent=True) or {}
        bridge = body.get("bridge") or engine.config.get("outputs", "hue", "bridge")
        if not bridge:
            try:
                bridges = hue_pairing.discover_bridges()
            except Exception as exc:
                return jsonify({"error": f"discovery failed: {exc}"}), 400
            if not bridges:
                return jsonify({"error": "no bridge found, enter its IP"}), 400
            bridge = bridges[0]
        try:
            keys = hue_pairing.pair(bridge)
        except Exception as exc:
            return jsonify({"error": str(exc), "bridge": bridge}), 400
        engine.config.update({"outputs": {"hue": {"bridge": bridge, **keys}}})
        return jsonify({"bridge": bridge, "paired": True})

    @app.get("/api/hue/areas")
    def hue_areas():
        hue = engine.config.get("outputs", "hue")
        if not hue.get("bridge") or not hue.get("app_key"):
            return jsonify({"error": "pair with the bridge first"}), 400
        try:
            return jsonify(hue_pairing.list_entertainment_areas(hue["bridge"], hue["app_key"]))
        except Exception as exc:
            return jsonify({"error": str(exc)}), 400

    return app


def run_server(engine, host: str, port: int) -> None:
    app = create_app(engine)
    app.run(host=host, port=port, threaded=True, use_reloader=False)
