#!/usr/bin/env python3
"""Static HTTP server with correct JS module MIME type and deterministic no-cache."""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[1]
PORT = int(os.environ.get('PORT', 8765))
class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()

if __name__ == '__main__':
    print(f'Ice Snake Lab: http://127.0.0.1:{PORT}/games/snake/', flush=True)
    ThreadingHTTPServer(('127.0.0.1', PORT), Handler).serve_forever()