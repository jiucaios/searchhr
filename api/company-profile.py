"""API endpoint for company profile search."""

import json
import sys
import os
from http.server import BaseHTTPRequestHandler
from io import BytesIO

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        self._handle_request()
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps({'status': 'ok'}, ensure_ascii=False).encode('utf-8'))
    
    def _handle_request(self):
        try:
            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            
            from company_profile_search import company_profile_search_api
            
            data = json.loads(body or '{}')
            
            result = company_profile_search_api(
                company_name=data.get("company_name", ""),
                company_website=data.get("company_website", ""),
                job_description=data.get("job_description", ""),
                max_iterations=int(data.get("max_iterations", 2)),
            )
            
            response_body = json.dumps(result, ensure_ascii=False)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(response_body.encode('utf-8'))
            
        except Exception as exc:
            import traceback
            error = {
                "status": "failed",
                "reason": str(exc),
                "traceback": traceback.format_exc(),
                "missing_info": ["有效输入", "公司信息"],
            }
            
            response_body = json.dumps(error, ensure_ascii=False)
            
            self.send_response(500)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(response_body.encode('utf-8'))
    
    def log_message(self, format, *args):
        # Suppress default logging
        pass
