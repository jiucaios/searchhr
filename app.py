"""Flask application entry point for local development and Vercel deployment."""

import os
from flask import Flask, request, jsonify, send_from_directory
from company_profile_search import company_profile_search_api

app = Flask(__name__, static_folder='.')

@app.route('/api/company-profile', methods=['POST'])
def company_profile():
    try:
        data = request.get_json()
        
        result = company_profile_search_api(
            company_name=data.get("company_name", ""),
            company_website=data.get("company_website", ""),
            job_description=data.get("job_description", ""),
            max_iterations=int(data.get("max_iterations", 2)),
        )
        
        return jsonify(result)
    except Exception as exc:
        import traceback
        error = {
            "status": "failed",
            "reason": str(exc),
            "traceback": traceback.format_exc(),
            "missing_info": ["有效输入", "公司信息"],
        }
        return jsonify(error), 500

@app.route('/')
def index():
    """Serve the main HTML page."""
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    """Serve static files (CSS, JS, images, etc.)"""
    if os.path.exists(os.path.join('.', path)):
        return send_from_directory('.', path)
    else:
        # Fallback to index.html for client-side routing
        return send_from_directory('.', 'index.html')

if __name__ == '__main__':
    port = int(os.environ.get('SERVER_PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=True)