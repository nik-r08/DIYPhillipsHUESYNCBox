"""Command line entry point:  python -m syncbox --config config.yaml"""
from __future__ import annotations

import argparse
import logging
import signal
import threading

from .config import Config
from .engine import Engine


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="DIY Hue Sync Box")
    p.add_argument("--config", default="config.yaml", help="YAML config file (created if missing)")
    p.add_argument("--source", help="override capture device: /dev/video0, 0, synthetic, file:movie.mp4")
    p.add_argument("--mode", choices=["game", "video", "movie", "music", "static", "calibrate"])
    p.add_argument("--no-web", action="store_true", help="do not start the web UI")
    p.add_argument("--no-audio", action="store_true")
    p.add_argument("--duration", type=float, help="run for N seconds then exit (testing)")
    p.add_argument("-v", "--verbose", action="store_true")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    overrides: dict = {}
    if args.source:
        overrides["capture"] = {"device": args.source}
    if args.mode:
        overrides["processing"] = {"mode": args.mode}
    config = Config(args.config, overrides)
    if not config.path.exists():
        config.save()
        logging.info("wrote default config to %s", config.path)

    engine = Engine(config, enable_audio=not args.no_audio)

    if not args.no_web:
        from .web import run_server
        web = config.get("web")
        threading.Thread(target=run_server, args=(engine, web["host"], int(web["port"])), name="web", daemon=True).start()
        logging.info("web UI on http://%s:%s", web["host"], web["port"])

    signal.signal(signal.SIGTERM, lambda *_: engine.stop())
    signal.signal(signal.SIGINT, lambda *_: engine.stop())
    engine.run(duration=args.duration)
    return 0
