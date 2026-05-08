"""Test endpoint to verify API is working."""

import json

def app(environ, start_response):
    """WSGI application for Vercel Python runtime"""
    
    method = environ.get('REQUEST_METHOD', 'GET')
    
    # Handle CORS preflight
    if method == 'OPTIONS':
        status = '200 OK'
        headers = [
            ('Content-Type', 'application/json; charset=utf-8'),
            ('Access-Control-Allow-Origin', '*'),
            ('Access-Control-Allow-Methods', 'GET, POST, OPTIONS'),
            ('Access-Control-Allow-Headers', 'Content-Type')
        ]
        start_response(status, headers)
        return [json.dumps({'status': 'ok'}, ensure_ascii=False).encode('utf-8')]
    
    # Normal response
    status = '200 OK'
    headers = [
        ('Content-Type', 'application/json; charset=utf-8'),
        ('Access-Control-Allow-Origin', '*')
    ]
    start_response(status, headers)
    
    response = {
        'status': 'success',
        'message': 'Test endpoint is working!',
        'method': method
    }
    
    return [json.dumps(response, ensure_ascii=False).encode('utf-8')]

# Export both names for compatibility
handler = app
