"""API endpoint for company profile search."""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def handler(event, context):
    try:
        from company_profile_search import company_profile_search_api
        
        body = json.loads(event.get('body', '{}') or '{}')
        result = company_profile_search_api(
            company_name=body.get("company_name", ""),
            company_website=body.get("company_website", ""),
            job_description=body.get("job_description", ""),
            max_iterations=int(body.get("max_iterations", 2)),
        )
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json; charset=utf-8',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
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
