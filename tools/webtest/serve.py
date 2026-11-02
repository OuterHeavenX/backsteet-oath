#!/usr/bin/env python3
"""Minimal static HTTP server for testing the web export (no special headers, like itch.io)."""
import http.server, socketserver, sys, os, functools
root = sys.argv[1] if len(sys.argv) > 1 else "."
port = int(sys.argv[2]) if len(sys.argv) > 2 else 8765
class Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map,
                      ".wasm": "application/wasm", ".pck": "application/octet-stream", ".js": "application/javascript"}
    def log_message(self, *a):
        pass
class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True
with Server(("127.0.0.1", port), functools.partial(Handler, directory=os.path.abspath(root))) as httpd:
    httpd.serve_forever()
