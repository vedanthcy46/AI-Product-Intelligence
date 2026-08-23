"""
serve.py -- Serve the frontend dashboard locally (STATIC ONLY).

Note: this server has no upload endpoint. For the Upload page to actually
process files, run `python frontend/server.py` instead (Flask backend with
POST /api/process). This script only exists for browsing an existing
frontend/data snapshot.

Optionally regenerates the data contract first, then serves the static app.

Usage:
    python frontend/serve.py [--port 8000] [--generate] [--limit 50]
"""

import argparse
import http.server
import os
import subprocess
import sys
import webbrowser

ROOT = os.path.dirname(os.path.abspath(__file__))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--generate", action="store_true",
                        help="Regenerate frontend/data from the pipeline before serving")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    if args.generate or not os.path.exists(os.path.join(ROOT, "data", "products.json")):
        cmd = [sys.executable, "generate_data.py"]
        if args.limit:
            cmd.append(f"--limit {args.limit}")
        subprocess.run(cmd, cwd=ROOT, check=True)

    handler = http.server.SimpleHTTPRequestHandler

    class QuietHandler(handler):
        def log_message(self, format, *args):  # noqa: A002 - shadowing base signature
            sys.stderr.write(f"[serve] {self.address_string()} {format % args}\n")

    os.chdir(ROOT)
    server = http.server.ThreadingHTTPServer(("127.0.0.1", args.port), QuietHandler)
    url = f"http://127.0.0.1:{args.port}/index.html"
    print(f"Serving frontend at {url}")
    print("[serve] Static-only server: the Upload page cannot process files here.")
    print("[serve] For a working Upload flow run: python frontend/server.py")
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")


if __name__ == "__main__":
    main()