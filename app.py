"""Flask application for company profile search - compatible with Vercel."""

from __future__ import annotations

import json
import os
from pathlib import Path

from flask import Flask, request, send_from_directory

# Add parent directory to path for imports
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from company_profile_search import company_profile_search_api


ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / "public"

app = Flask(__name__, static_folder=str(PUBLIC), static_url_path="")


@app.route("/")
@app.route("/index.html")
def index():
    return send_from_directory(str(PUBLIC), "index.html")


@app.route("/<path:path>")
def serve_static(path):
    return send_from_directory(str(PUBLIC), path)


@app.route("/api/company-profile", methods=["POST", "OPTIONS"])
def company_profile():
    if request.method == "OPTIONS":
        return "", 200, {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        }
    
    try:
        payload = request.get_json(silent=True) or {}
        result = company_profile_search_api(
            company_name=payload.get("company_name", ""),
            company_website=payload.get("company_website", ""),
            job_description=payload.get("job_description", ""),
            max_iterations=int(payload.get("max_iterations", 2)),
        )
        return result, 200, {
            'Content-Type': 'application/json; charset=utf-8',
            'Access-Control-Allow-Origin': '*'
        }
    except Exception as exc:
        import traceback
        error = {
            "status": "failed",
            "reason": str(exc),
            "traceback": traceback.format_exc(),
            "missing_info": ["有效输入", "公司信息"],
        }
        return error, 500, {
            'Content-Type': 'application/json; charset=utf-8',
            'Access-Control-Allow-Origin': '*'
        }


def main() -> None:
    port = int(os.getenv("PORT", 8000))
    print(f"Company profile demo running at http://127.0.0.1:{port}")
    app.run(host="0.0.0.0", port=port, debug=True)


if __name__ == "__main__":
    main()
