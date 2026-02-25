"""
Lambda Handler: Document Management (Bedrock Agent Action Group)
Handles document upload, listing, and deletion using S3 metadata
"""
import json
import logging
import os
import uuid
import base64
from datetime import datetime
from typing import Dict, Any

import boto3

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS clients
s3_client = boto3.client('s3')
lambda_client = boto3.client('lambda')

# Environment variables
S3_BUCKET = os.environ['S3_BUCKET_NAME']
S3_DOCUMENTS_PREFIX = os.environ.get('S3_DOCUMENTS_PREFIX', 'documents/')
INDEXING_LAMBDA_ARN = os.environ.get('INDEXING_LAMBDA_ARN', '')


def list_documents(user_id: str = None) -> list:
    """List all documents from S3 (optionally filtered by user)"""
    try:
        response = s3_client.list_objects_v2(
            Bucket=S3_BUCKET,
            Prefix=S3_DOCUMENTS_PREFIX
        )

        documents = []
        for obj in response.get('Contents', []):
            # Skip the prefix folder itself
            if obj['Key'] == S3_DOCUMENTS_PREFIX:
                continue

            # Get object metadata
            try:
                head = s3_client.head_object(Bucket=S3_BUCKET, Key=obj['Key'])
                metadata = head.get('Metadata', {})
            except Exception:
                metadata = {}

            # Filter by user_id if specified
            if user_id and metadata.get('user_id') != user_id:
                continue

            documents.append({
                'document_id': metadata.get('document_id', ''),
                'filename': metadata.get('filename', obj['Key'].split('/')[-1]),
                's3_key': obj['Key'],
                'user_id': metadata.get('user_id', ''),
                'size': obj['Size'],
                'last_modified': obj['LastModified'].isoformat()
            })

        logger.info(f"Found {len(documents)} documents")
        return documents

    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}")
        raise


def get_document(doc_id: str) -> Dict[str, Any]:
    """Get document metadata from S3 by searching for doc_id in object metadata"""
    try:
        response = s3_client.list_objects_v2(
            Bucket=S3_BUCKET,
            Prefix=S3_DOCUMENTS_PREFIX
        )

        for obj in response.get('Contents', []):
            if obj['Key'] == S3_DOCUMENTS_PREFIX:
                continue
            try:
                head = s3_client.head_object(Bucket=S3_BUCKET, Key=obj['Key'])
                metadata = head.get('Metadata', {})
                if metadata.get('document_id') == doc_id:
                    return {
                        'document_id': doc_id,
                        'filename': metadata.get('filename', ''),
                        's3_key': obj['Key'],
                        'user_id': metadata.get('user_id', ''),
                        'size': obj['Size'],
                        'last_modified': obj['LastModified'].isoformat()
                    }
            except Exception:
                continue

        return None
    except Exception as e:
        logger.error(f"Error getting document: {str(e)}")
        raise


def delete_document(doc_id: str) -> bool:
    """Delete document from S3"""
    try:
        doc = get_document(doc_id)
        if not doc:
            return False

        s3_key = doc.get('s3_key')
        if s3_key:
            s3_client.delete_object(Bucket=S3_BUCKET, Key=s3_key)
            logger.info(f"Deleted from S3: {s3_key}")

        return True

    except Exception as e:
        logger.error(f"Error deleting document: {str(e)}")
        raise


def upload_document(filename: str, content_base64: str, user_id: str) -> Dict[str, Any]:
    """Upload document to S3 and trigger indexing"""
    try:
        # Generate document ID
        doc_id = str(uuid.uuid4())
        s3_key = f"{S3_DOCUMENTS_PREFIX}{doc_id}_{filename}"

        # Decode and upload to S3 with metadata
        content = base64.b64decode(content_base64)
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=content,
            ContentType='application/pdf',
            Metadata={
                'document_id': doc_id,
                'filename': filename,
                'user_id': user_id,
                'upload_timestamp': datetime.utcnow().isoformat(),
                'status': 'indexing'
            }
        )
        logger.info(f"Uploaded to S3: {s3_key}")

        # Trigger indexing Lambda asynchronously
        if INDEXING_LAMBDA_ARN:
            lambda_client.invoke(
                FunctionName=INDEXING_LAMBDA_ARN,
                InvocationType='Event',
                Payload=json.dumps({
                    'document_key': s3_key,
                    'document_id': doc_id,
                    'user_id': user_id
                })
            )
            logger.info(f"Triggered indexing Lambda for {doc_id}")

        return {
            'document_id': doc_id,
            'filename': filename,
            's3_key': s3_key,
            'user_id': user_id,
            'status': 'indexing'
        }

    except Exception as e:
        logger.error(f"Error uploading document: {str(e)}")
        raise


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for document management (Bedrock Agent Action Group)

    Supports:
    - POST /documents/upload
    - GET /documents/list
    - DELETE /documents/{doc_id}
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")

        # Parse Bedrock Agent event
        action_group = event.get('actionGroup', '')
        api_path = event.get('apiPath', '')
        http_method = event.get('httpMethod', 'GET')

        # Extract parameters
        parameters = event.get('parameters', [])
        param_dict = {p['name']: p['value'] for p in parameters}

        # Route based on API path and method
        if api_path == '/documents/list' and http_method == 'GET':
            user_id = param_dict.get('user_id')
            documents = list_documents(user_id)
            response_body = {'documents': documents, 'count': len(documents)}
            status_code = 200

        elif api_path == '/documents/upload' and http_method == 'POST':
            filename = param_dict.get('filename', 'document.pdf')
            content_base64 = param_dict.get('content_base64', '')
            user_id = param_dict.get('user_id', 'anonymous')

            if not content_base64:
                response_body = {'error': 'content_base64 is required'}
                status_code = 400
            else:
                doc_metadata = upload_document(filename, content_base64, user_id)
                response_body = {'message': 'Document uploaded successfully', 'document': doc_metadata}
                status_code = 200

        elif api_path.startswith('/documents/') and http_method == 'DELETE':
            doc_id = param_dict.get('doc_id', '')
            if not doc_id:
                response_body = {'error': 'doc_id is required'}
                status_code = 400
            else:
                success = delete_document(doc_id)
                if success:
                    response_body = {'message': 'Document deleted successfully', 'document_id': doc_id}
                    status_code = 200
                else:
                    response_body = {'error': 'Document not found'}
                    status_code = 404
        else:
            response_body = {'error': 'Invalid API path or method'}
            status_code = 400

        # Return Bedrock Agent response
        return {
            'messageVersion': '1.0',
            'response': {
                'actionGroup': action_group,
                'apiPath': api_path,
                'httpMethod': http_method,
                'httpStatusCode': status_code,
                'responseBody': {
                    'application/json': {
                        'body': json.dumps(response_body)
                    }
                }
            }
        }

    except Exception as e:
        logger.error(f"Error in document management: {str(e)}", exc_info=True)

        return {
            'messageVersion': '1.0',
            'response': {
                'actionGroup': event.get('actionGroup', ''),
                'apiPath': event.get('apiPath', ''),
                'httpMethod': event.get('httpMethod', 'GET'),
                'httpStatusCode': 500,
                'responseBody': {
                    'application/json': {
                        'body': json.dumps({
                            'error': str(e),
                            'message': 'Internal server error'
                        })
                    }
                }
            }
        }
