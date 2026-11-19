#!/usr/bin/env python3
"""Minimal static HTTP server for testing the web export (no special headers, like itch.io).

Usage: serve.py [root] [port] [--gzip]
  --gzip   answer requests that accept it with gzip-compressed bodies (level 6), to measure what a host that
           compresses on the fly would transfer. Off by default: the plain server sends every file as-is.
"""
import http.server, socketserver, sys, os, functools, gzip
args = [a for a in sys.argv[1:] if not a.startswith("--")]
GZIP = "--gzip" in sys.argv
root = args[0] if len(args) > 0 else "."
port = int(args[1]) if len(args) > 1 else 8765
_gz_cache = {}
class Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map,
                      ".wasm": "application/wasm", ".pck": "application/octet-stream", ".js": "application/javascript"}
    def log_message(self, *a):
        pass
    def do_GET(self):
        path = self.translate_path(self.path)
        if not (GZIP and "gzip" in self.headers.get("Accept-Encoding", "") and os.path.isfile(path)):
            return super().do_GET()
        st = os.stat(path)
        etag = '"%x-%x-gz"' % (st.st_mtime_ns, st.st_size)
        if self.headers.get("If-None-Match") == etag:
            self.send_response(304)
            self.send_header("ETag", etag)
            self.end_headers()
            return
        key = (path, st.st_mtime_ns, st.st_size)
        if key not in _gz_cache:
            with open(path, "rb") as f:
                _gz_cache[key] = gzip.compress(f.read(), 6)
        body = _gz_cache[key]
        self.send_response(200)
        self.send_header("Content-Type", self.guess_type(path))
        self.send_header("Content-Encoding", "gzip")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("ETag", etag)
        self.end_headers()
        self.wfile.write(body)
class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True
with Server(("127.0.0.1", port), functools.partial(Handler, directory=os.path.abspath(root))) as httpd:
    httpd.serve_forever()
