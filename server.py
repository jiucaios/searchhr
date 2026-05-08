"""Local web demo server for the company profile search tool."""

from __future__ import annotations

import json
import mimetypes
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

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


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 8000), DemoHandler)
    print("Company profile demo running at http://127.0.0.1:8000")
    server.serve_forever()


if __name__ == "__main__":
    main()
