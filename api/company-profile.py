import json
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def handler(request):
    """
    Vercel Python Serverless Function
    Uses Vercel's Python runtime request/response format
    """
    
    # Get HTTP method
    method = request.get('method', 'GET')
    
    # Handle CORS preflight
    if method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json; charset=utf-8',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            },
            'body': json.dumps({'status': 'ok'}, ensure_ascii=False)
        }
    
    # Only allow POST method
    if method != 'POST':
        return {
            'statusCode': 405,
            'headers': {
                'Content-Type': 'application/json; charset=utf-8',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': 'Method not allowed'}, ensure_ascii=False)
        }
    
    try:
        # Parse request body
        body_str = request.get('body', '{}') or '{}'
        if isinstance(body_str, bytes):
            body_str = body_str.decode('utf-8')
        
        data = json.loads(body_str)
        
        # Import and call the company profile search function
        from company_profile_search import company_profile_search_api
        
        result = company_profile_search_api(
            company_name=data.get("company_name", ""),
            company_website=data.get("company_website", ""),
            job_description=data.get("job_description", ""),
            max_iterations=int(data.get("max_iterations", 1)),  # Default to 1 for faster response
        )
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json; charset=utf-8',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(result, ensure_ascii=False)
        }
        
    except Exception as exc:
        import traceback
        error = {
            "status": "failed",
            "reason": str(exc),
            "traceback": traceback.format_exc(),
            "missing_info": ["有效输入", "公司信息"],
        }
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json; charset=utf-8',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(error, ensure_ascii=False)
        }
