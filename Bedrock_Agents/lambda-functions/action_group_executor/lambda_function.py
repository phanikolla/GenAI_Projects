import json
import boto3
import os
from datetime import datetime
import uuid
from decimal import Decimal

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
tickets_table = dynamodb.Table(os.environ.get('TICKETS_TABLE', 'support-tickets-dev'))
customers_table = dynamodb.Table(os.environ.get('CUSTOMERS_TABLE', 'customers-dev'))

class DecimalEncoder(json.JSONEncoder):
    """Helper class to convert DynamoDB Decimal types to JSON"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

def lambda_handler(event, context):
    """
    Main handler for Bedrock Agent action group requests
    Routes requests to appropriate tool handlers
    """
    print(f"Received event: {json.dumps(event)}")
    
    try:
        # Extract action group information
        api_path = event.get('apiPath', '')
        http_method = event.get('httpMethod', 'POST')
        action_group = event.get('actionGroup', '')
        parameters = event.get('parameters', [])
        
        # Convert parameters list to dictionary
        params = {p['name']: p.get('value', '') for p in parameters}
        
        print(f"API Path: {api_path}, Method: {http_method}, Params: {params}")
        
        # Route to appropriate handler
        if '/tickets' in api_path and http_method == 'POST' and 'escalate' not in api_path:
            result = create_support_ticket(params)
        elif '/customers' in api_path and http_method == 'GET':
            result = retrieve_customer_info(params)
        elif '/tickets' in api_path and http_method == 'PUT':
            result = update_ticket_status(params)
        elif '/tickets/search' in api_path:
            result = search_tickets(params)
        elif '/tickets/escalate' in api_path:
            result = escalate_support_ticket(params)
        else:
            result = {
                'success': False,
                'error': f'Unknown action: {api_path} with method {http_method}'
            }
        
        return format_response(result)
        
    except Exception as e:
        print(f"Error in lambda_handler: {str(e)}")
        return format_response({
            'success': False,
            'error': f'Internal error: {str(e)}'
        }, status_code=500)

def create_support_ticket(params):
    """Create a new support ticket"""
    try:
        ticket_id = f"TKT-{str(uuid.uuid4())[:8].upper()}"
        timestamp = datetime.utcnow().isoformat()
        
        ticket_item = {
            'ticket_id': ticket_id,
            'customer_id': params.get('customer_id', 'UNKNOWN'),
            'issue_description': params.get('issue_description', ''),
            'issue_category': params.get('issue_category', 'other'),
            'priority': params.get('priority', 'medium'),
            'status': 'open',
            'created_at': timestamp,
            'updated_at': timestamp,
            'assigned_agent': 'bedrock-agent',
            'resolution_notes': ''
        }
        
        tickets_table.put_item(Item=ticket_item)
        
        # Update customer ticket count
        try:
            customers_table.update_item(
                Key={'customer_id': ticket_item['customer_id']},
                UpdateExpression='ADD total_tickets :inc SET updated_at = :updated',
                ExpressionAttributeValues={
                    ':inc': 1,
                    ':updated': timestamp
                }
            )
        except Exception as e:
            print(f"Warning: Could not update customer stats: {str(e)}")
        
        return {
            'success': True,
            'ticket_id': ticket_id,
            'message': f'Support ticket {ticket_id} created successfully',
            'ticket_details': ticket_item
        }
        
    except Exception as e:
        print(f"Error creating ticket: {str(e)}")
        return {
            'success': False,
            'error': f'Failed to create ticket: {str(e)}'
        }

def retrieve_customer_info(params):
    """Retrieve customer information and recent tickets"""
    try:
        customer_id = params.get('customer_id')
        
        if not customer_id:
            return {'success': False, 'error': 'customer_id is required'}
        
        # Get or create customer record
        response = customers_table.get_item(Key={'customer_id': customer_id})
        
        if 'Item' not in response:
            # Create new customer record
            timestamp = datetime.utcnow().isoformat()
            customer_data = {
                'customer_id': customer_id,
                'created_at': timestamp,
                'updated_at': timestamp,
                'account_status': 'active',
                'total_tickets': 0,
                'lifetime_value': Decimal('0.0')
            }
            customers_table.put_item(Item=customer_data)
        else:
            customer_data = response['Item']
        
        # Get recent tickets using GSI
        tickets_response = tickets_table.query(
            IndexName='customer-index',
            KeyConditionExpression='customer_id = :cid',
            ExpressionAttributeValues={':cid': customer_id},
            Limit=10,
            ScanIndexForward=False
        )
        
        recent_tickets = tickets_response.get('Items', [])
        open_tickets = [t for t in recent_tickets if t.get('status') == 'open']
        
        return {
            'success': True,
            'customer': json.loads(json.dumps(customer_data, cls=DecimalEncoder)),
            'recent_tickets': json.loads(json.dumps(recent_tickets, cls=DecimalEncoder)),
            'open_tickets_count': len(open_tickets),
            'total_tickets_count': len(recent_tickets)
        }
        
    except Exception as e:
        print(f"Error retrieving customer: {str(e)}")
        return {
            'success': False,
            'error': f'Failed to retrieve customer info: {str(e)}'
        }

def update_ticket_status(params):
    """Update ticket status and resolution notes"""
    try:
        ticket_id = params.get('ticket_id')
        new_status = params.get('new_status')
        resolution_notes = params.get('resolution_notes', '')
        
        if not ticket_id or not new_status:
            return {
                'success': False,
                'error': 'ticket_id and new_status are required'
            }
        
        timestamp = datetime.utcnow().isoformat()
        
        update_expression = 'SET #status = :status, updated_at = :updated'
        expression_values = {
            ':status': new_status,
            ':updated': timestamp
        }
        
        if resolution_notes:
            update_expression += ', resolution_notes = :notes'
            expression_values[':notes'] = resolution_notes
        
        response = tickets_table.update_item(
            Key={'ticket_id': ticket_id},
            UpdateExpression=update_expression,
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues=expression_values,
            ReturnValues='ALL_NEW'
        )
        
        return {
            'success': True,
            'message': f'Ticket {ticket_id} updated to {new_status}',
            'updated_ticket': json.loads(json.dumps(response['Attributes'], cls=DecimalEncoder))
        }
        
    except Exception as e:
        print(f"Error updating ticket: {str(e)}")
        return {
            'success': False,
            'error': f'Failed to update ticket: {str(e)}'
        }

def search_tickets(params):
    """Search tickets by customer and filters"""
    try:
        customer_id = params.get('customer_id')
        status_filter = params.get('status')
        priority_filter = params.get('priority')
        limit = int(params.get('limit', 10))
        
        if not customer_id:
            return {'success': False, 'error': 'customer_id is required'}
        
        # Query using GSI
        tickets_response = tickets_table.query(
            IndexName='customer-index',
            KeyConditionExpression='customer_id = :cid',
            ExpressionAttributeValues={':cid': customer_id},
            Limit=limit,
            ScanIndexForward=False
        )
        
        tickets = tickets_response.get('Items', [])
        
        # Apply filters
        if status_filter:
            tickets = [t for t in tickets if t.get('status') == status_filter]
        
        if priority_filter:
            tickets = [t for t in tickets if t.get('priority') == priority_filter]
        
        return {
            'success': True,
            'tickets_found': len(tickets),
            'tickets': json.loads(json.dumps(tickets, cls=DecimalEncoder))
        }
        
    except Exception as e:
        print(f"Error searching tickets: {str(e)}")
        return {
            'success': False,
            'error': f'Failed to search tickets: {str(e)}'
        }

def escalate_support_ticket(params):
    """Escalate ticket to human support"""
    try:
        ticket_id = params.get('ticket_id')
        reason = params.get('reason', 'Requires human review')
        
        if not ticket_id:
            return {'success': False, 'error': 'ticket_id is required'}
        
        timestamp = datetime.utcnow().isoformat()
        
        response = tickets_table.update_item(
            Key={'ticket_id': ticket_id},
            UpdateExpression='SET #status = :status, escalation_reason = :reason, updated_at = :updated, escalated_at = :escalated',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':status': 'escalated',
                ':reason': reason,
                ':updated': timestamp,
                ':escalated': timestamp
            },
            ReturnValues='ALL_NEW'
        )
        
        # In production, you would trigger SNS notification here
        print(f"Ticket {ticket_id} escalated. Reason: {reason}")
        
        return {
            'success': True,
            'message': f'Ticket {ticket_id} escalated to human support team',
            'escalation_reason': reason,
            'updated_ticket': json.loads(json.dumps(response['Attributes'], cls=DecimalEncoder))
        }
        
    except Exception as e:
        print(f"Error escalating ticket: {str(e)}")
        return {
            'success': False,
            'error': f'Failed to escalate ticket: {str(e)}'
        }

def format_response(response_body, status_code=200):
    """Format response for Bedrock Agent"""
    return {
        'messageVersion': '1.0',
        'response': {
            'actionGroup': 'customer-support-tools',
            'apiPath': '/response',
            'httpMethod': 'POST',
            'httpStatusCode': status_code,
            'responseBody': {
                'application/json': {
                    'body': json.dumps(response_body, cls=DecimalEncoder)
                }
            }
        }
    }
