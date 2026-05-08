"""Test endpoint to verify API is working."""

import json

def handler(request):
    """Simple test endpoint"""
    
    method = request.get('method', 'GET')
    
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json; charset=utf-8',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({
            'status': 'success',
            'message': 'Test endpoint is working!',
            'method': method
        }, ensure_ascii=False)
    }
