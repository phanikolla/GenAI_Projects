"""
Lambda Handler: Document Indexing
Processes uploaded PDFs, creates embeddings, and stores FAISS index in S3
"""
import json
import logging
import os
import tempfile
from typing import Dict, Any

import boto3
from langchain_aws import BedrockEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter

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
CHUNK_SIZE = int(os.environ.get('CHUNK_SIZE', '1000'))
CHUNK_OVERLAP = int(os.environ.get('CHUNK_OVERLAP', '200'))


def get_embeddings():
    """Initialize Bedrock embeddings"""
    return BedrockEmbeddings(
        region_name=AWS_REGION,
        model_id=EMBEDDING_MODEL_ID
    )


def download_from_s3(bucket: str, key: str, local_path: str):
    """Download file from S3"""
    logger.info(f"Downloading s3://{bucket}/{key} to {local_path}")
    s3_client.download_file(bucket, key, local_path)


def upload_to_s3(local_path: str, bucket: str, key: str):
    """Upload file to S3"""
    logger.info(f"Uploading {local_path} to s3://{bucket}/{key}")
    s3_client.upload_file(local_path, bucket, key)


def process_document(pdf_path: str, doc_id: str) -> FAISS:
    """
    Load PDF, split into chunks, create embeddings, and build FAISS index
    """
    # Load PDF
    logger.info(f"Loading PDF: {pdf_path}")
    loader = PyPDFLoader(pdf_path)
    pages = loader.load()
    logger.info(f"Loaded {len(pages)} pages")
    
    # Add metadata
    for page in pages:
        page.metadata['document_id'] = doc_id
    
    # Split into chunks
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", " ", ""]
    )
    chunks = splitter.split_documents(pages)
    logger.info(f"Split into {len(chunks)} chunks")
    
    # Create embeddings and FAISS index
    embeddings = get_embeddings()
    logger.info("Building FAISS index...")
    vectorstore = FAISS.from_documents(chunks, embeddings)
    logger.info(f"FAISS index created with {vectorstore.index.ntotal} vectors")
    
    return vectorstore


def merge_or_create_index(new_vectorstore: FAISS, doc_id: str) -> FAISS:
    """
    Merge new vectors with existing FAISS index or create new one
    """
    index_key = f"{S3_FAISS_PREFIX}index.faiss"
    pkl_key = f"{S3_FAISS_PREFIX}index.pkl"
    
    try:
        # Try to download existing index
        with tempfile.TemporaryDirectory() as tmpdir:
            local_index = os.path.join(tmpdir, "index.faiss")
            local_pkl = os.path.join(tmpdir, "index.pkl")
            
            download_from_s3(S3_BUCKET, index_key, local_index)
            download_from_s3(S3_BUCKET, pkl_key, local_pkl)
            
            # Load existing index
            embeddings = get_embeddings()
            existing_vectorstore = FAISS.load_local(
                tmpdir, 
                embeddings,
                index_name="index",
                allow_dangerous_deserialization=True
            )
            logger.info(f"Loaded existing index with {existing_vectorstore.index.ntotal} vectors")
            
            # Merge indexes
            existing_vectorstore.merge_from(new_vectorstore)
            logger.info(f"Merged index now has {existing_vectorstore.index.ntotal} vectors")
            
            return existing_vectorstore
            
    except Exception as e:
        logger.info(f"No existing index found or error loading: {e}. Creating new index.")
        return new_vectorstore


def save_index_to_s3(vectorstore: FAISS):
    """Save FAISS index to S3"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Save locally
        vectorstore.save_local(tmpdir, index_name="index")
        
        # Upload to S3
        index_file = os.path.join(tmpdir, "index.faiss")
        pkl_file = os.path.join(tmpdir, "index.pkl")
        
        upload_to_s3(index_file, S3_BUCKET, f"{S3_FAISS_PREFIX}index.faiss")
        upload_to_s3(pkl_file, S3_BUCKET, f"{S3_FAISS_PREFIX}index.pkl")
        
        logger.info("FAISS index saved to S3")


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for document indexing
    
    Expected event:
    {
        "document_key": "documents/doc123.pdf",
        "document_id": "doc123",
        "user_id": "user456"
    }
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # Parse event
        document_key = event['document_key']
        doc_id = event['document_id']
        user_id = event.get('user_id', 'unknown')
        
        # Download PDF from S3
        with tempfile.TemporaryDirectory() as tmpdir:
            local_pdf = os.path.join(tmpdir, f"{doc_id}.pdf")
            download_from_s3(S3_BUCKET, document_key, local_pdf)
            
            # Process document and create FAISS index
            new_vectorstore = process_document(local_pdf, doc_id)
            
            # Merge with existing index or create new
            final_vectorstore = merge_or_create_index(new_vectorstore, doc_id)
            
            # Save to S3
            save_index_to_s3(final_vectorstore)
        
        # Return success
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Document indexed successfully',
                'document_id': doc_id,
                'vectors_count': final_vectorstore.index.ntotal
            })
        }
        
    except Exception as e:
        logger.error(f"Error processing document: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'message': 'Failed to index document'
            })
        }
