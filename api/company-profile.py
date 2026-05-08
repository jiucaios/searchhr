"""API endpoint for company profile search."""

import json
from company_profile_search import company_profile_search_api

def handler(event, context):
    try:
        body = json.loads(event.get('body', '{}') or '{}')
        result = company_profile_search_api(
            company_name=body.get("company_name", ""),
            company_website=body.get("company_website", ""),
            job_description=body.get("job_description", ""),
            max_iterations=int(body.get("max_iterations", 2)),
        )
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json; charset=utf-8', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps(result, ensure_ascii=False)
        }
    except Exception as exc:
        error = {
            "status": "failed",
            "reason": str(exc),
            "missing_info": ["有效输入", "公司信息"],
        }
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json; charset=utf-8', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps(error, ensure_ascii=False)
        }
