"""Web demo server for the company profile search tool - supports both local and Vercel."""

from __future__ import annotations

import json
import mimetypes
from pathlib import Path
from urllib.parse import urlparse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from company_profile_search import company_profile_search_api


ROOT = Path(__file__).resolve().parent
FRONTEND = ROOT / "frontend"


class DemoHandler(SimpleHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path in {"/", "/index.html"}:
            self._send_file(FRONTEND / "index.html")
            return
        target = FRONTEND / parsed.path.lstrip("/")
        if target.exists() and target.is_file():
            self._send_file(target)
            return
        self.send_error(404, "Not found")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/api/company-profile":
            self.send_error(404, "Not found")
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            result = company_profile_search_api(
                company_name=payload.get("company_name", ""),
                company_website=payload.get("company_website", ""),
                job_description=payload.get("job_description", ""),
                max_iterations=int(payload.get("max_iterations", 2)),
            )
            self._send_json(result)
        except Exception as exc:
            self._send_json(
                {
                    "status": "failed",
                    "reason": str(exc),
                    "missing_info": ["有效输入", "公司信息"],
                },
                status=500,
            )

    def _send_file(self, path: Path) -> None:
        content = path.read_bytes()
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _send_json(self, payload: dict, status: int = 200) -> None:
        content = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


def application(environ, start_response):
    """WSGI application for Vercel deployment."""
    from io import BytesIO

    class MockRequest:
        def __init__(self, environ):
            self.environ = environ
            self.rfile = BytesIO()
            self.wfile = BytesIO()
            
        def send_response(self, status):
            self.status = status
            
        def send_header(self, name, value):
            if not hasattr(self, 'headers'):
                self.headers = []
            self.headers.append((name, value))
            
        def end_headers(self):
            pass

    method = environ['REQUEST_METHOD']
    path = environ.get('PATH_INFO', '/')
    length = int(environ.get('CONTENT_LENGTH', 0))
    
    if method == 'POST' and path == '/api/company-profile':
        try:
            body = environ['wsgi.input'].read(length)
            payload = json.loads(body.decode('utf-8') or '{}')
            result = company_profile_search_api(
                company_name=payload.get("company_name", ""),
                company_website=payload.get("company_website", ""),
                job_description=payload.get("job_description", ""),
                max_iterations=int(payload.get("max_iterations", 2)),
            )
            content = json.dumps(result, ensure_ascii=False, indent=2).encode('utf-8')
            status = '200 OK'
            headers = [
                ('Content-Type', 'application/json; charset=utf-8'),
                ('Content-Length', str(len(content)))
            ]
        except Exception as exc:
            error = {
                "status": "failed",
                "reason": str(exc),
                "missing_info": ["有效输入", "公司信息"],
            }
            content = json.dumps(error, ensure_ascii=False).encode('utf-8')
            status = '500 Internal Server Error'
            headers = [
                ('Content-Type', 'application/json; charset=utf-8'),
                ('Content-Length', str(len(content)))
            ]
    elif method == 'GET':
        if path in {"/", "/index.html"}:
            target = FRONTEND / "index.html"
        else:
            target = FRONTEND / path.lstrip("/")
            
        if target.exists() and target.is_file():
            content = target.read_bytes()
            content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
            status = '200 OK'
            headers = [
                ('Content-Type', content_type),
                ('Content-Length', str(len(content)))
            ]
        else:
            content = b'404 Not Found'
            status = '404 Not Found'
            headers = [
                ('Content-Type', 'text/plain'),
                ('Content-Length', str(len(content)))
            ]
    else:
        content = b'404 Not Found'
        status = '404 Not Found'
        headers = [
            ('Content-Type', 'text/plain'),
            ('Content-Length', str(len(content)))
        ]
    
    start_response(status, headers)
    return [content]


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 8000), DemoHandler)
    print("Company profile demo running at http://127.0.0.1:8000")
    server.serve_forever()


if __name__ == "__main__":
    main()
