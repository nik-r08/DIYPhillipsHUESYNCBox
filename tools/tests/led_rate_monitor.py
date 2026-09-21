#!/usr/bin/env python3
"""Log HyperHDR's LED update rate for hours (T2). Label UNT: written to the JSON API docs.

Connects to HyperHDR's raw JSON server (TCP 19444), subscribes to the LED colour stream
({"command":"ledcolors","subcommand":"ledstream-start"}) and counts messages per second.
Writes CSV: timestamp,updates_per_sec,max_gap_ms,dropped(gap>100ms)

    python3 led_rate_monitor.py --host 127.0.0.1 --hours 8 --out ledrate.csv
"""
import argparse
import json
import socket
import time


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=19444)
    ap.add_argument("--hours", type=float, default=8)
    ap.add_argument("--out", default="ledrate.csv")
    ap.add_argument("--target", type=float, default=50)
    a = ap.parse_args()
    s = socket.create_connection((a.host, a.port), timeout=10)
    s.sendall((json.dumps({"command": "ledcolors", "subcommand": "ledstream-start", "tan": 1}) + "\n").encode())
    end = time.time() + a.hours * 3600
    buf = b""
    count, last, max_gap, dropped, t_sec = 0, time.time(), 0.0, 0, time.time()
    below = 0
    with open(a.out, "a") as fh:
        fh.write("timestamp,updates_per_sec,max_gap_ms,dropped\n")
        while time.time() < end:
            try:
                data = s.recv(65536)
            except socket.timeout:
                data = b""
            if not data:
                fh.write(f"{time.strftime('%F %T')},0,{(time.time()-last)*1000:.0f},1\n"); fh.flush()
                print("stream stalled"); dropped += 1; time.sleep(1); continue
            buf += data
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                if b"ledcolors" in line or b"led-colors" in line:
                    now = time.time(); gap = (now - last) * 1000; last = now
                    max_gap = max(max_gap, gap); count += 1
                    if gap > 100: dropped += 1
            now = time.time()
            if now - t_sec >= 1.0:
                rate = count / (now - t_sec)
                fh.write(f"{time.strftime('%F %T')},{rate:.1f},{max_gap:.0f},{dropped}\n"); fh.flush()
                if rate < a.target: below += 1
                count, max_gap, t_sec = 0, 0.0, now
    print(f"done. seconds below {a.target} Hz: {below}; gaps > 100 ms: {dropped}")
    print("PASS" if below == 0 and dropped == 0 else "FAIL")


if __name__ == "__main__":
    main()
