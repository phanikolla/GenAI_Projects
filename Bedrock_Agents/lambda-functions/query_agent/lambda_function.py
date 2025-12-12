import json
import boto3
import uuid
import os
from datetime import datetime

# Initialize Bedrock client
bedrock_agent_runtime = boto3.client('bedrock-agent-runtime')

def lambda_handler(event, context):
    """
    Entry point for agent invocation via API Gateway
    """
    print(f"Received event: {json.dumps(event)}")
    
    try:
        # Parse request body
        if isinstance(event.get('body'), str):
            body = json.loads(event.get('body', '{}'))
        else:
            body = event.get('body', {})
        
        user_message = body.get('message', body.get('prompt', ''))
        customer_id = body.get('customer_id', 'unknown')
        session_id = body.get('session_id', str(uuid.uuid4()))
        
        # Get agent configuration from environment
        agent_id = os.environ.get('AGENT_ID')
        agent_alias_id = os.environ.get('AGENT_ALIAS_ID', 'TSTALIASID')
        
        if not agent_id:
            return {
                'statusCode': 500,
                'headers': get_cors_headers(),
                'body': json.dumps({
                    'error': 'Agent not configured. Please set AGENT_ID environment variable.'
                })
            }
        
        if not user_message:
            return {
                'statusCode': 400,
                'headers': get_cors_headers(),
                'body': json.dumps({
                    'error': 'Message is required in request body'
                })
            }
        
        print(f"Invoking agent {agent_id} with message: {user_message}")
        
        # Invoke Bedrock Agent
        response = bedrock_agent_runtime.invoke_agent(
            agentId=agent_id,
            agentAliasId=agent_alias_id,
            sessionId=session_id,
            inputText=user_message,
            enableTrace=True
        )
        
        # Process streaming response
        final_response = ""
        trace_data = []
        
        event_stream = response.get('completion')
        
        for event in event_stream:
            if 'chunk' in event:
                chunk = event['chunk']
                if 'bytes' in chunk:
                    final_response += chunk['bytes'].decode('utf-8')
            
            if 'trace' in event:
                trace_data.append(event['trace'])
        
        print(f"Agent response: {final_response}")
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'response': final_response,
                'sessionId': session_id,
                'customer_id': customer_id,
                'timestamp': datetime.utcnow().isoformat(),
                'trace': trace_data if os.environ.get('INCLUDE_TRACE') == 'true' else None
            })
        }
        
    except Exception as e:
        print(f"Error invoking agent: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            'statusCode': 500,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'error': str(e),
                'message': 'Failed to process request'
            })
        }

def get_cors_headers():
    """Return CORS headers for API Gateway"""
    return {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key',
        'Access-Control-Allow-Methods': 'POST,OPTIONS'
    }
