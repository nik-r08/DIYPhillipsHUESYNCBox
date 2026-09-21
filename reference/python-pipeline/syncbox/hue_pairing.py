"""One-time pairing with a Hue Bridge (v2) and Entertainment Area discovery."""
from __future__ import annotations

import warnings

try:
    import requests
    from urllib3.exceptions import InsecureRequestWarning
    warnings.simplefilter("ignore", InsecureRequestWarning)
except Exception:  # pragma: no cover
    requests = None


def _need_requests():
    if requests is None:
        raise RuntimeError("pip install requests")


def discover_bridges() -> list[str]:
    """IPs of Hue bridges on the LAN via Philips' discovery service."""
    _need_requests()
    r = requests.get("https://discovery.meethue.com/", timeout=5)
    r.raise_for_status()
    return [b["internalipaddress"] for b in r.json()]


def pair(bridge_ip: str, devicetype: str = "syncbox#raspberrypi") -> dict:
    """Press the link button on the bridge first.  Returns app_key + client_key."""
    _need_requests()
    r = requests.post(
        f"https://{bridge_ip}/api",
        json={"devicetype": devicetype, "generateclientkey": True},
        verify=False,
        timeout=5,
    )
    r.raise_for_status()
    body = r.json()[0]
    if "error" in body:
        raise RuntimeError(body["error"].get("description", "pairing failed"))
    return {"app_key": body["success"]["username"], "client_key": body["success"]["clientkey"]}


def list_entertainment_areas(bridge_ip: str, app_key: str) -> list[dict]:
    _need_requests()
    r = requests.get(
        f"https://{bridge_ip}/clip/v2/resource/entertainment_configuration",
        headers={"hue-application-key": app_key},
        verify=False,
        timeout=5,
    )
    r.raise_for_status()
    areas = []
    for item in r.json().get("data", []):
        areas.append({
            "id": item["id"],
            "name": item.get("metadata", {}).get("name", "?"),
            "status": item.get("status"),
            "channels": [
                {"channel_id": c["channel_id"], "position": c.get("position", {})}
                for c in item.get("channels", [])
            ],
        })
    return areas
