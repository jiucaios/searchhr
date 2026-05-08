import json
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def handler(req, res):
    """
    Vercel Python Serverless Function
    req: IncomingMessage (Node.js http.IncomingMessage)
    res: ServerResponse (Node.js http.ServerResponse)
    """
    
    # Handle CORS preflight
    if req.method == 'OPTIONS':
        res.writeHead(200, {
            'Content-Type': 'application/json; charset=utf-8',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        })
        res.end(json.dumps({'status': 'ok'}, ensure_ascii=False))
        return
    
    # Only allow POST method
    if req.method != 'POST':
        res.writeHead(405, {
            'Content-Type': 'application/json; charset=utf-8',
            'Access-Control-Allow-Origin': '*'
        })
        res.end(json.dumps({'error': 'Method not allowed'}, ensure_ascii=False))
        return
    
    # Collect request body
    body_parts = []
    
    def on_data(chunk):
        body_parts.append(chunk)
    
    def on_end():
        try:
            body = b''.join(body_parts).decode('utf-8')
            process_request(body, res)
        except Exception as exc:
            import traceback
            error = {
                "status": "failed",
                "reason": str(exc),
                "traceback": traceback.format_exc(),
                "missing_info": ["有效输入", "公司信息"],
            }
            res.writeHead(500, {
                'Content-Type': 'application/json; charset=utf-8',
                'Access-Control-Allow-Origin': '*'
            })
            res.end(json.dumps(error, ensure_ascii=False))
    
    req.on('data', on_data)
    req.on('end', on_end)

def process_request(body, res):
    """Process the request after body is fully received"""
    try:
        from company_profile_search import company_profile_search_api
        
        data = json.loads(body or '{}')
        
        result = company_profile_search_api(
            company_name=data.get("company_name", ""),
            company_website=data.get("company_website", ""),
            job_description=data.get("job_description", ""),
            max_iterations=int(data.get("max_iterations", 2)),
        )
        
        res.writeHead(200, {
            'Content-Type': 'application/json; charset=utf-8',
            'Access-Control-Allow-Origin': '*'
        })
        res.end(json.dumps(result, ensure_ascii=False))
        
    except Exception as exc:
        import traceback
        error = {
            "status": "failed",
            "reason": str(exc),
            "traceback": traceback.format_exc(),
            "missing_info": ["有效输入", "公司信息"],
        }
        res.writeHead(500, {
            'Content-Type': 'application/json; charset=utf-8',
            'Access-Control-Allow-Origin': '*'
        })
        res.end(json.dumps(error, ensure_ascii=False))
