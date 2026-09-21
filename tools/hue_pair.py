#!/usr/bin/env python3
"""Pair with a Hue Bridge and list Entertainment Areas.

    python3 tools/hue_pair.py                # auto-discover the bridge
    python3 tools/hue_pair.py 192.168.1.2    # or give its IP

Press the round link button on the bridge, then run this within 30 s.  The
printed keys go into pi/config.yaml under outputs.hue.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pi"))

from syncbox import hue_pairing


def main():
    bridge = sys.argv[1] if len(sys.argv) > 1 else None
    if not bridge:
        bridges = hue_pairing.discover_bridges()
        if not bridges:
            sys.exit("no bridge found - pass its IP address")
        bridge = bridges[0]
        print(f"found bridge at {bridge}")
    try:
        keys = hue_pairing.pair(bridge)
    except RuntimeError as exc:
        sys.exit(f"pairing failed: {exc} (press the link button and retry)")
    print("\nPaste into pi/config.yaml:\n")
    print("outputs:\n  hue:\n    enabled: true")
    print(f"    bridge: {bridge}")
    print(f"    app_key: {keys['app_key']}")
    print(f"    client_key: {keys['client_key']}")
    areas = hue_pairing.list_entertainment_areas(bridge, keys["app_key"])
    if not areas:
        print("\nNo Entertainment Areas yet - create one in the Hue app (Settings > Entertainment areas).")
        return
    print("\nEntertainment areas:")
    for a in areas:
        print(f"  entertainment_id: {a['id']}   # {a['name']}, {len(a['channels'])} channels")
        for ch in a["channels"]:
            p = ch["position"]
            print(f"      channel {ch['channel_id']}: x={p.get('x')} y={p.get('y')} z={p.get('z')}")


if __name__ == "__main__":
    main()
