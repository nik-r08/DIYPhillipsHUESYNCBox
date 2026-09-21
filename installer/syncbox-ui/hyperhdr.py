"""Minimal HyperHDR JSON-RPC client (HTTP on port 8090).

Endpoint: POST {base}/json-rpc with a JSON body such as
    {"command": "componentstate", "componentstate": {"component": "LEDDEVICE", "state": true}}
Reference: https://github.com/awawa-dev/HyperHDR/wiki/JSON-API and
sources/api/JSONRPC_schema in the HyperHDR repository (v22).
Evidence label: command names and shapes are taken from the schema files; the client itself
was exercised only against the fake server in tools/tests/fake_hyperhdr.py (SYN).
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

BASE = os.environ.get("HYPERHDR_URL", "http://127.0.0.1:8090")


class HyperHDRError(RuntimeError):
    pass


def call(command: str, timeout: float = 3.0, **fields) -> dict:
    body = {"command": command, **fields}
    req = urllib.request.Request(
        f"{BASE}/json-rpc", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            out = json.loads(resp.read().decode() or "{}")
    except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
        raise HyperHDRError(f"HyperHDR unreachable at {BASE}: {exc}") from exc
    if isinstance(out, dict) and out.get("success") is False:
        raise HyperHDRError(out.get("error", "unknown error"))
    return out


def serverinfo() -> dict:
    return call("serverinfo").get("info", {})


def set_component(component: str, state: bool) -> dict:
    return call("componentstate", componentstate={"component": component, "state": bool(state)})


def leds_on(state: bool) -> dict:
    return set_component("LEDDEVICE", state)


def set_adjustment(**adj) -> dict:
    """brightness 0..100, saturationGain / luminanceGain floats, etc."""
    return call("adjustment", adjustment=adj)


def set_config(section: str, values: dict) -> dict:
    """Persist a settings section. HyperHDR: {"command":"config","subcommand":"setconfig","config":{section:{...}}}"""
    return call("config", subcommand="setconfig", config={section: values})


def get_config() -> dict:
    return call("config", subcommand="getconfig").get("info", {})


def set_effect(name: str, priority: int = 1, duration: int = 0) -> dict:
    return call("effect", effect={"name": name}, priority=priority, duration=duration)


def clear(priority: int = 1) -> dict:
    return call("clear", priority=priority)


def set_color(rgb, priority: int = 1, duration: int = 0) -> dict:
    return call("color", color=list(rgb), priority=priority, duration=duration)


def signal_state() -> dict:
    """Summarise what serverinfo tells us: components on/off, active priority, grabber."""
    info = serverinfo()
    comps = {c.get("name"): c.get("enabled") for c in info.get("components", [])}
    prios = info.get("priorities", [])
    active = next((p for p in prios if p.get("visible")), prios[0] if prios else {})
    return {
        "leds_enabled": comps.get("LEDDEVICE", None),
        "grabber_enabled": comps.get("VIDEOGRABBER", comps.get("V4L", None)),
        "active_source": active.get("componentId") or active.get("owner"),
        "active_priority": active.get("priority"),
        "video_active": (active.get("componentId") in ("VIDEOGRABBER", "V4L", "GRABBER")),
        "hyperhdr_version": info.get("hyperhdr", {}).get("version") or info.get("version"),
    }
