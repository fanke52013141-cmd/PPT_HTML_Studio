"""Local GET-only review server with same-origin access to isolated assets."""
import argparse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import urllib.request
from pathlib import Path
import re
from urllib.parse import urlsplit


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', required=True)
    parser.add_argument('--port', type=int, default=8016)
    args = parser.parse_args()

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=args.directory, **kw)

        def do_GET(self):
            if self.path.startswith(('/api/', '/fonts/', '/annotation_player.bundle.js')):
                try:
                    request = urllib.request.Request('http://127.0.0.1:8015' + self.path,
                        headers={'Range': self.headers['Range']} if self.headers.get('Range') else {})
                    with urllib.request.urlopen(request, timeout=30) as response:
                        data = response.read()
                        self.send_response(response.status)
                        self.send_header('Content-Type', response.headers.get('Content-Type', 'application/octet-stream'))
                        self.send_header('Content-Length', str(len(data)))
                        for key in ('Accept-Ranges', 'Content-Range'):
                            if response.headers.get(key):
                                self.send_header(key, response.headers[key])
                        self.end_headers()
                        self.wfile.write(data)
                except Exception:
                    self.send_error(502, 'Isolated acceptance asset unavailable')
                return
            if urlsplit(self.path).path.startswith('/audio/'):
                path = Path(self.translate_path(self.path)).resolve()
                if not path.is_relative_to(Path(args.directory).resolve()) or not path.is_file() or path.suffix != '.mp3':
                    self.send_error(404)
                    return
                data = path.read_bytes()
                start, end = 0, len(data)-1
                header = self.headers.get('Range')
                if header:
                    match = re.fullmatch(r'bytes=(\d*)-(\d*)', header)
                    if not match or not any(match.groups()):
                        self.send_error(416)
                        return
                    first, last = match.groups()
                    if first:
                        start = int(first)
                        end = min(end, int(last)) if last else end
                    else:
                        start = max(0, len(data)-int(last))
                    if start > end or start >= len(data):
                        self.send_response(416)
                        self.send_header('Content-Range', f'bytes */{len(data)}')
                        self.end_headers()
                        return
                self.send_response(206 if header else 200)
                self.send_header('Content-Type', 'audio/mpeg')
                self.send_header('Accept-Ranges', 'bytes')
                self.send_header('Content-Length', str(end-start+1))
                if header:
                    self.send_header('Content-Range', f'bytes {start}-{end}/{len(data)}')
                self.end_headers()
                self.wfile.write(data[start:end+1])
                return
            super().do_GET()

        def log_message(self, *args):
            pass

    ThreadingHTTPServer(('127.0.0.1', args.port), Handler).serve_forever()


if __name__ == '__main__':
    main()
