"""
AWS Cognito Authentication Module
"""
import logging
from typing import Dict, Optional

import boto3
from botocore.exceptions import ClientError
from jose import jwt, JWTError
import requests

from config import settings

logger = logging.getLogger(__name__)

# Cognito client
cognito_client = boto3.client('cognito-idp', region_name=settings.COGNITO_REGION)

# Cache for JWKS
_jwks_cache = None


def get_jwks():
    """Get JSON Web Key Set from Cognito"""
    global _jwks_cache
    
    if _jwks_cache:
        return _jwks_cache
    
    jwks_url = f"https://cognito-idp.{settings.COGNITO_REGION}.amazonaws.com/{settings.COGNITO_USER_POOL_ID}/.well-known/jwks.json"
    response = requests.get(jwks_url)
    _jwks_cache = response.json()
    return _jwks_cache


def verify_token(token: str) -> Optional[Dict]:
    """
    Verify JWT token from Cognito
    Returns user info if valid, None otherwise
    """
    try:
        # Get JWKS
        jwks = get_jwks()
        
        # Decode token header to get kid
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header['kid']
        
        # Find the correct key
        key = None
        for jwk in jwks['keys']:
            if jwk['kid'] == kid:
                key = jwk
                break
        
        if not key:
            logger.error("Public key not found in JWKS")
            return None
        
        # Verify and decode token
        payload = jwt.decode(
            token,
            key,
            algorithms=['RS256'],
            audience=settings.COGNITO_CLIENT_ID,
            issuer=f"https://cognito-idp.{settings.COGNITO_REGION}.amazonaws.com/{settings.COGNITO_USER_POOL_ID}"
        )
        
        return payload
        
    except JWTError as e:
        logger.error(f"JWT verification failed: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Token verification error: {str(e)}")
        return None


def create_user(email: str, password: str, name: str = None) -> Dict:
    """
    Create a new user in Cognito
    """
    try:
        user_attributes = [
            {'Name': 'email', 'Value': email}
        ]
        
        if name:
            user_attributes.append({'Name': 'name', 'Value': name})
        
        response = cognito_client.sign_up(
            ClientId=settings.COGNITO_CLIENT_ID,
            Username=email,
            Password=password,
            UserAttributes=user_attributes
        )
        
        logger.info(f"User created: {email}")
        return response
        
    except ClientError as e:
        logger.error(f"Error creating user: {str(e)}")
        raise Exception(e.response['Error']['Message'])


def authenticate_user(email: str, password: str) -> Dict:
    """
    Authenticate user and get tokens
    """
    try:
        response = cognito_client.initiate_auth(
            ClientId=settings.COGNITO_CLIENT_ID,
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={
                'USERNAME': email,
                'PASSWORD': password
            }
        )
        
        logger.info(f"User authenticated: {email}")
        return response
        
    except ClientError as e:
        logger.error(f"Authentication error: {str(e)}")
        raise Exception(e.response['Error']['Message'])


def refresh_access_token(refresh_token: str) -> Dict:
    """
    Refresh access token using refresh token
    """
    try:
        response = cognito_client.initiate_auth(
            ClientId=settings.COGNITO_CLIENT_ID,
            AuthFlow='REFRESH_TOKEN_AUTH',
            AuthParameters={
                'REFRESH_TOKEN': refresh_token
            }
        )
        
        logger.info("Token refreshed successfully")
        return response
        
    except ClientError as e:
        logger.error(f"Token refresh error: {str(e)}")
        raise Exception(e.response['Error']['Message'])


def confirm_signup(email: str, confirmation_code: str) -> Dict:
    """
    Confirm user signup with verification code
    """
    try:
        response = cognito_client.confirm_sign_up(
            ClientId=settings.COGNITO_CLIENT_ID,
            Username=email,
            ConfirmationCode=confirmation_code
        )
        
        logger.info(f"User confirmed: {email}")
        return response
        
    except ClientError as e:
        logger.error(f"Confirmation error: {str(e)}")
        raise Exception(e.response['Error']['Message'])
