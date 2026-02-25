"""
Lambda Handler: RAG Retrieval (Bedrock Agent Action Group)
Retrieves relevant context from FAISS index for a given question
"""
import json
import logging
import os
import tempfile
from typing import Dict, Any, List

import boto3
from langchain_aws import BedrockEmbeddings
from langchain_community.vectorstores import FAISS

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS clients
s3_client = boto3.client('s3')

# Environment variables
S3_BUCKET = os.environ['S3_BUCKET_NAME']
S3_FAISS_PREFIX = os.environ.get('S3_FAISS_PREFIX', 'faiss-indexes/')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')  # AWS_REGION is automatically set by Lambda
EMBEDDING_MODEL_ID = os.environ.get('EMBEDDING_MODEL_ID', 'amazon.titan-embed-text-v2:0')
SEARCH_K = int(os.environ.get('SEARCH_K', '4'))
SEARCH_FETCH_K = int(os.environ.get('SEARCH_FETCH_K', '8'))
SEARCH_TYPE = os.environ.get('SEARCH_TYPE', 'mmr')

# Cache for FAISS index
_vectorstore_cache = None


def get_embeddings():
    """Initialize Bedrock embeddings"""
    return BedrockEmbeddings(
        region_name=AWS_REGION,
        model_id=EMBEDDING_MODEL_ID
    )


def load_faiss_index() -> FAISS:
    """Load FAISS index from S3 (with caching)"""
    global _vectorstore_cache
    
    if _vectorstore_cache is not None:
        logger.info("Using cached FAISS index")
        return _vectorstore_cache
    
    logger.info("Loading FAISS index from S3...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Download index files
        index_key = f"{S3_FAISS_PREFIX}index.faiss"
        pkl_key = f"{S3_FAISS_PREFIX}index.pkl"
        
        local_index = os.path.join(tmpdir, "index.faiss")
        local_pkl = os.path.join(tmpdir, "index.pkl")
        
        s3_client.download_file(S3_BUCKET, index_key, local_index)
        s3_client.download_file(S3_BUCKET, pkl_key, local_pkl)
        
        # Load FAISS index
        embeddings = get_embeddings()
        vectorstore = FAISS.load_local(
            tmpdir,
            embeddings,
            index_name="index",
            allow_dangerous_deserialization=True
        )
        
        logger.info(f"Loaded FAISS index with {vectorstore.index.ntotal} vectors")
        
        # Cache for subsequent invocations
        _vectorstore_cache = vectorstore
        
        return vectorstore


def retrieve_context(question: str, k: int = SEARCH_K) -> List[Dict[str, Any]]:
    """
    Retrieve relevant documents for the question
    """
    vectorstore = load_faiss_index()
    
    # Create retriever
    if SEARCH_TYPE == 'mmr':
        retriever = vectorstore.as_retriever(
            search_type='mmr',
            search_kwargs={'k': k, 'fetch_k': SEARCH_FETCH_K}
        )
    else:
        retriever = vectorstore.as_retriever(
            search_type='similarity',
            search_kwargs={'k': k}
        )
    
    # Retrieve documents
    docs = retriever.invoke(question)
    logger.info(f"Retrieved {len(docs)} documents")
    
    # Format results
    results = []
    for i, doc in enumerate(docs):
        results.append({
            'content': doc.page_content,
            'metadata': doc.metadata,
            'rank': i + 1
        })
    
    return results


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for RAG retrieval (Bedrock Agent Action Group)
    
    Bedrock Agent event format:
    {
        "actionGroup": "RAGRetrieval",
        "apiPath": "/retrieve",
        "httpMethod": "POST",
        "parameters": [
            {"name": "question", "type": "string", "value": "What is the leave policy?"},
            {"name": "k", "type": "number", "value": "4"}
        ],
        "requestBody": {...}
    }
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # Parse Bedrock Agent event
        action_group = event.get('actionGroup', '')
        api_path = event.get('apiPath', '')
        
        # Extract parameters
        parameters = event.get('parameters', [])
        param_dict = {p['name']: p['value'] for p in parameters}
        
        question = param_dict.get('question', '')
        k = int(param_dict.get('k', SEARCH_K))
        
        if not question:
            return {
                'messageVersion': '1.0',
                'response': {
                    'actionGroup': action_group,
                    'apiPath': api_path,
                    'httpMethod': event.get('httpMethod', 'POST'),
                    'httpStatusCode': 400,
                    'responseBody': {
                        'application/json': {
                            'body': json.dumps({'error': 'Question parameter is required'})
                        }
                    }
                }
            }
        
        # Retrieve context
        results = retrieve_context(question, k)
        
        # Format response for Bedrock Agent
        response_body = {
            'question': question,
            'context': results,
            'total_results': len(results)
        }
        
        return {
            'messageVersion': '1.0',
            'response': {
                'actionGroup': action_group,
                'apiPath': api_path,
                'httpMethod': event.get('httpMethod', 'POST'),
                'httpStatusCode': 200,
                'responseBody': {
                    'application/json': {
                        'body': json.dumps(response_body)
                    }
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Error retrieving context: {str(e)}", exc_info=True)
        
        return {
            'messageVersion': '1.0',
            'response': {
                'actionGroup': event.get('actionGroup', ''),
                'apiPath': event.get('apiPath', ''),
                'httpMethod': event.get('httpMethod', 'POST'),
                'httpStatusCode': 500,
                'responseBody': {
                    'application/json': {
                        'body': json.dumps({
                            'error': str(e),
                            'message': 'Failed to retrieve context'
                        })
                    }
                }
            }
        }
