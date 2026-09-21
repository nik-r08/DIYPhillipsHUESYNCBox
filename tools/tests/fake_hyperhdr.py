"""A fake HyperHDR JSON-RPC server for testing syncbox-ui without hardware.
Records every request; answers serverinfo with a configurable state.
    python3 tools/tests/fake_hyperhdr.py 8090
"""
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

STATE = {"leds": True, "video": True, "requests": []}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # quiet
        pass

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(n) or b"{}")
        STATE["requests"].append(body)
        cmd = body.get("command")
        resp = {"success": True, "command": cmd}
        if cmd == "componentstate":
            cs = body["componentstate"]
            if cs["component"] == "LEDDEVICE":
                STATE["leds"] = cs["state"]
        elif cmd == "serverinfo":
            resp["info"] = {
                "components": [{"name": "LEDDEVICE", "enabled": STATE["leds"]}, {"name": "VIDEOGRABBER", "enabled": True}],
                "priorities": [{"priority": 250, "visible": STATE["video"], "componentId": "VIDEOGRABBER"}],
                "hyperhdr": {"version": "22.0.0.0-fake"},
            }
        elif cmd == "config" and body.get("subcommand") == "setconfig":
            if "bogus" in body.get("config", {}):
                resp = {"success": False, "error": "unknown section"}
        data = json.dumps(resp).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def serve(port: int):
    httpd = HTTPServer(("127.0.0.1", port), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


if __name__ == "__main__":
    serve(int(sys.argv[1]) if len(sys.argv) > 1 else 8090)
    print("fake HyperHDR listening")
    threading.Event().wait()
