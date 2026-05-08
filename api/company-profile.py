import json
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def app(environ, start_response):
    """WSGI application for Vercel Python runtime"""
    
    method = environ.get('REQUEST_METHOD', 'GET')
    
    # Handle CORS preflight
    if method == 'OPTIONS':
        status = '200 OK'
        headers = [
            ('Content-Type', 'application/json; charset=utf-8'),
            ('Access-Control-Allow-Origin', '*'),
            ('Access-Control-Allow-Methods', 'POST, OPTIONS'),
            ('Access-Control-Allow-Headers', 'Content-Type')
        ]
        start_response(status, headers)
        return [json.dumps({'status': 'ok'}, ensure_ascii=False).encode('utf-8')]
    
    # Only allow POST method
    if method != 'POST':
        status = '405 Method Not Allowed'
        headers = [
            ('Content-Type', 'application/json; charset=utf-8'),
            ('Access-Control-Allow-Origin', '*')
        ]
        start_response(status, headers)
        return [json.dumps({'error': 'Method not allowed'}, ensure_ascii=False).encode('utf-8')]
    
    try:
        # Read request body
        content_length = int(environ.get('CONTENT_LENGTH', 0))
        if content_length > 0:
            body_bytes = environ['wsgi.input'].read(content_length)
            body_str = body_bytes.decode('utf-8')
        else:
            body_str = '{}'
        
        data = json.loads(body_str or '{}')
        
        # Import and call the company profile search function
        from company_profile_search import company_profile_search_api
        
        result = company_profile_search_api(
            company_name=data.get("company_name", ""),
            company_website=data.get("company_website", ""),
            job_description=data.get("job_description", ""),
            max_iterations=int(data.get("max_iterations", 1)),
        )
        
        status = '200 OK'
        headers = [
            ('Content-Type', 'application/json; charset=utf-8'),
            ('Access-Control-Allow-Origin', '*')
        ]
        start_response(status, headers)
        return [json.dumps(result, ensure_ascii=False).encode('utf-8')]
        
    except Exception as exc:
        import traceback
        error = {
            "status": "failed",
            "reason": str(exc),
            "traceback": traceback.format_exc(),
            "missing_info": ["有效输入", "公司信息"],
        }
        status = '500 Internal Server Error'
        headers = [
            ('Content-Type', 'application/json; charset=utf-8'),
            ('Access-Control-Allow-Origin', '*')
        ]
        start_response(status, headers)
        return [json.dumps(error, ensure_ascii=False).encode('utf-8')]

# Export both names for compatibility
handler = app
