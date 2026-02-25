"""
RAG Service - Interfaces with Bedrock Agent and AWS services
"""
import json
import logging
import uuid
from typing import Dict, List, Optional

import boto3
from botocore.exceptions import ClientError

from config import settings

logger = logging.getLogger(__name__)

# AWS clients
s3_client = boto3.client('s3', region_name=settings.AWS_REGION)
bedrock_agent_runtime = boto3.client('bedrock-agent-runtime', region_name=settings.AWS_REGION)
lambda_client = boto3.client('lambda', region_name=settings.AWS_REGION)


class RAGService:
    """Service for RAG operations using Bedrock Agent"""
    
    def __init__(self):
        self.agent_id = settings.BEDROCK_AGENT_ID
        self.agent_alias_id = settings.BEDROCK_AGENT_ALIAS_ID
        self.s3_bucket = settings.S3_BUCKET_NAME
        self.documents_prefix = settings.S3_DOCUMENTS_PREFIX
    
    async def upload_document(self, filename: str, content: bytes, user_id: str) -> Dict:
        """
        Upload document to S3 and trigger indexing
        """
        try:
            # Generate document ID
            doc_id = str(uuid.uuid4())
            s3_key = f"{self.documents_prefix}{doc_id}_{filename}"
            
            # Upload to S3
            s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=s3_key,
                Body=content,
                ContentType='application/pdf',
                Metadata={
                    'user_id': user_id,
                    'document_id': doc_id,
                    'filename': filename
                }
            )
            logger.info(f"Uploaded document to S3: {s3_key}")
            
            # Trigger indexing Lambda (async)
            # Note: In production, get Lambda ARN from environment
            try:
                lambda_client.invoke(
                    FunctionName='serverless-rag-indexing',
                    InvocationType='Event',
                    Payload=json.dumps({
                        'document_key': s3_key,
                        'document_id': doc_id,
                        'user_id': user_id
                    })
                )
                logger.info(f"Triggered indexing for document: {doc_id}")
            except Exception as e:
                logger.warning(f"Could not trigger indexing Lambda: {e}")
            
            return {
                'document_id': doc_id,
                'filename': filename,
                's3_key': s3_key,
                'status': 'indexing'
            }
            
        except ClientError as e:
            logger.error(f"Error uploading document: {str(e)}")
            raise
    
    async def list_documents(self, user_id: str) -> List[Dict]:
        """
        List documents for a user from S3
        """
        try:
            response = s3_client.list_objects_v2(
                Bucket=self.s3_bucket,
                Prefix=self.documents_prefix
            )
            
            documents = []
            for obj in response.get('Contents', []):
                # Get object metadata
                metadata_response = s3_client.head_object(
                    Bucket=self.s3_bucket,
                    Key=obj['Key']
                )
                metadata = metadata_response.get('Metadata', {})
                
                # Filter by user_id
                if metadata.get('user_id') == user_id:
                    documents.append({
                        'document_id': metadata.get('document_id'),
                        'filename': metadata.get('filename'),
                        's3_key': obj['Key'],
                        'size': obj['Size'],
                        'last_modified': obj['LastModified'].isoformat()
                    })
            
            return documents
            
        except ClientError as e:
            logger.error(f"Error listing documents: {str(e)}")
            raise
    
    async def delete_document(self, doc_id: str, user_id: str) -> bool:
        """
        Delete document from S3
        """
        try:
            # List objects to find the document
            response = s3_client.list_objects_v2(
                Bucket=self.s3_bucket,
                Prefix=self.documents_prefix
            )
            
            for obj in response.get('Contents', []):
                # Check metadata
                metadata_response = s3_client.head_object(
                    Bucket=self.s3_bucket,
                    Key=obj['Key']
                )
                metadata = metadata_response.get('Metadata', {})
                
                if metadata.get('document_id') == doc_id and metadata.get('user_id') == user_id:
                    # Delete object
                    s3_client.delete_object(
                        Bucket=self.s3_bucket,
                        Key=obj['Key']
                    )
                    logger.info(f"Deleted document: {doc_id}")
                    return True
            
            return False
            
        except ClientError as e:
            logger.error(f"Error deleting document: {str(e)}")
            raise
    
    async def query(self, question: str, user_id: str, session_id: Optional[str] = None) -> Dict:
        """
        Query using Bedrock Agent
        """
        try:
            # Generate session ID if not provided
            if not session_id:
                session_id = str(uuid.uuid4())
            
            # Invoke Bedrock Agent
            response = bedrock_agent_runtime.invoke_agent(
                agentId=self.agent_id,
                agentAliasId=self.agent_alias_id,
                sessionId=session_id,
                inputText=question,
                enableTrace=True
            )
            
            # Process streaming response
            answer = ""
            trace = None
            
            for event in response['completion']:
                if 'chunk' in event:
                    chunk = event['chunk']
                    if 'bytes' in chunk:
                        answer += chunk['bytes'].decode('utf-8')
                
                if 'trace' in event:
                    trace = event['trace']
            
            logger.info(f"Query completed for session: {session_id}")
            
            return {
                'answer': answer,
                'session_id': session_id,
                'trace': trace,
                'sources': self._extract_sources_from_trace(trace) if trace else []
            }
            
        except ClientError as e:
            logger.error(f"Error querying Bedrock Agent: {str(e)}")
            raise
    
    def _extract_sources_from_trace(self, trace: Dict) -> List[Dict]:
        """
        Extract source documents from agent trace
        """
        sources = []
        
        # Parse trace to extract retrieval results
        # This depends on the trace structure from Bedrock Agent
        if trace and 'trace' in trace:
            trace_data = trace['trace']
            if 'orchestrationTrace' in trace_data:
                orch_trace = trace_data['orchestrationTrace']
                if 'observation' in orch_trace:
                    observation = orch_trace['observation']
                    if 'actionGroupInvocationOutput' in observation:
                        output = observation['actionGroupInvocationOutput']
                        # Extract sources from output
                        # Implementation depends on action group response format
                        pass
        
        return sources
    
    async def get_query_history(self, user_id: str, limit: int = 10) -> List[Dict]:
        """
        Get query history for a user
        Note: This would require a DynamoDB table to store query history
        """
        # Placeholder - implement with DynamoDB
        return []
