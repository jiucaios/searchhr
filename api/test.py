"""Test endpoint to verify API is working."""

import json

def handler(event, context):
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json; charset=utf-8',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({
            'status': 'success',
            'message': 'API is working!',
            'event': event
        }, ensure_ascii=False)
    }
