"""
Query Lambda - Wraps Bedrock Agent Runtime invoke_agent
Handles /query requests from API Gateway
"""
import json
import os
import uuid
import boto3
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Bedrock Agent config from environment
AGENT_ID = os.environ.get('BEDROCK_AGENT_ID')
AGENT_ALIAS_ID = os.environ.get('BEDROCK_AGENT_ALIAS_ID')

bedrock_agent_runtime = boto3.client('bedrock-agent-runtime')


def handler(event, context):
    """
    Lambda handler for API Gateway proxy integration.
    Expects JSON body: {"question": "...", "session_id": "..."}
    """
    logger.info(f"Event: {json.dumps(event)}")

    try:
        # Parse body
        body = json.loads(event.get('body', '{}'))
        question = body.get('question', '')
        session_id = body.get('session_id') or str(uuid.uuid4())

        if not question:
            return _response(400, {'error': 'question is required'})

        # Invoke Bedrock Agent
        response = bedrock_agent_runtime.invoke_agent(
            agentId=AGENT_ID,
            agentAliasId=AGENT_ALIAS_ID,
            sessionId=session_id,
            inputText=question,
            enableTrace=True
        )

        # Process streaming response
        answer = ""
        sources = []
        trace_data = None

        for event_chunk in response.get('completion', []):
            if 'chunk' in event_chunk:
                chunk = event_chunk['chunk']
                if 'bytes' in chunk:
                    answer += chunk['bytes'].decode('utf-8')

            if 'trace' in event_chunk:
                trace_data = event_chunk['trace']
                # Extract sources from trace
                trace_part = trace_data.get('trace', {})
                orch = trace_part.get('orchestrationTrace', {})
                obs = orch.get('observation', {})
                action_obs = obs.get('actionGroupInvocationOutput', {})
                if action_obs.get('text'):
                    try:
                        parsed = json.loads(action_obs['text'])
                        if isinstance(parsed, dict) and 'sources' in parsed:
                            sources = parsed['sources']
                    except (json.JSONDecodeError, KeyError):
                        pass

        return _response(200, {
            'answer': answer,
            'session_id': session_id,
            'sources': sources
        })

    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        return _response(500, {'error': str(e)})


def _response(status_code, body):
    """Build API Gateway proxy response with CORS headers."""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
            'Access-Control-Allow-Methods': 'POST,OPTIONS'
        },
        'body': json.dumps(body)
    }
