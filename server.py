"""Web demo server for the company profile search tool - supports both local and Vercel."""

from __future__ import annotations

import json
from pathlib import Path

from flask import Flask, request, send_from_directory

from company_profile_search import company_profile_search_api


ROOT = Path(__file__).resolve().parent
FRONTEND = ROOT / "public"

app = Flask(__name__, static_folder=str(FRONTEND), static_url_path="")


@app.route("/")
@app.route("/index.html")
def index():
    return send_from_directory(str(FRONTEND), "index.html")


@app.route("/<path:path>")
def serve_static(path):
    return send_from_directory(str(FRONTEND), path)


@app.route("/api/company-profile", methods=["POST"])
def company_profile():
    try:
        payload = request.get_json(silent=True) or {}
        result = company_profile_search_api(
            company_name=payload.get("company_name", ""),
            company_website=payload.get("company_website", ""),
            job_description=payload.get("job_description", ""),
            max_iterations=int(payload.get("max_iterations", 2)),
        )
        return result, 200, {"Content-Type": "application/json; charset=utf-8"}
    except Exception as exc:
        error = {
            "status": "failed",
            "reason": str(exc),
            "missing_info": ["有效输入", "公司信息"],
        }
        return error, 500, {"Content-Type": "application/json; charset=utf-8"}


def main() -> None:
    print("Company profile demo running at http://127.0.0.1:8000")
    app.run(host="127.0.0.1", port=8000, debug=True)


# Expose app for Vercel
if __name__ == "__main__":
    main()
