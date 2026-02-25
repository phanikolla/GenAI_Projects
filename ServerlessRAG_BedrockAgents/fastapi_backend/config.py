"""
Configuration settings for FastAPI backend
"""
import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    # AWS
    AWS_REGION: str = os.getenv('AWS_REGION', 'us-east-1')
    AWS_PROFILE: str = os.getenv('AWS_PROFILE', 'default')
    AWS_ACCOUNT_ID: str = os.getenv('AWS_ACCOUNT_ID', '')
    
    # S3
    S3_BUCKET_NAME: str = os.getenv('S3_BUCKET_NAME', 'serverless-rag-vectors')
    S3_DOCUMENTS_PREFIX: str = os.getenv('S3_DOCUMENTS_PREFIX', 'documents/')
    
    # Cognito
    COGNITO_USER_POOL_ID: str = os.getenv('COGNITO_USER_POOL_ID', '')
    COGNITO_CLIENT_ID: str = os.getenv('COGNITO_CLIENT_ID', '')
    COGNITO_REGION: str = os.getenv('COGNITO_REGION', 'us-east-1')
    
    # Bedrock Agent
    BEDROCK_AGENT_ID: str = os.getenv('BEDROCK_AGENT_ID', '')
    BEDROCK_AGENT_ALIAS_ID: str = os.getenv('BEDROCK_AGENT_ALIAS_ID', 'TSTALIASID')
    
    # API Gateway
    API_GATEWAY_URL: str = os.getenv('API_GATEWAY_URL', '')
    
    # FastAPI
    FASTAPI_HOST: str = os.getenv('FASTAPI_HOST', '0.0.0.0')
    FASTAPI_PORT: int = int(os.getenv('FASTAPI_PORT', '8000'))
    FASTAPI_DEBUG: bool = os.getenv('FASTAPI_DEBUG', 'false').lower() == 'true'
    
    class Config:
        env_file = '.env'
        case_sensitive = True
        extra = 'ignore'


settings = Settings()
