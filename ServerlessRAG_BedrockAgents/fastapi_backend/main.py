"""
FastAPI Backend for Serverless RAG with Bedrock Agents
Handles authentication, document management, and RAG queries
"""
import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles

from auth import verify_token, create_user, authenticate_user, refresh_access_token, confirm_signup
from config import settings
from models import (
    SignupRequest, LoginRequest, AuthResponse, RefreshRequest, ConfirmRequest,
    QueryRequest, QueryResponse, DocumentResponse
)
from rag_service import RAGService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="Serverless RAG API",
    description="RAG system with Bedrock Agents, API Gateway, and Cognito",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# RAG Service
rag_service = RAGService()


# Dependency for authentication
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token and return user info"""
    token = credentials.credentials
    user_info = verify_token(token)
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    return user_info


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "serverless-rag-api"}


# Authentication endpoints
@app.post("/auth/signup", response_model=AuthResponse)
async def signup(request: SignupRequest):
    """Register a new user"""
    try:
        result = create_user(request.email, request.password, request.name)
        return AuthResponse(
            message="User created successfully. Please check your email for verification.",
            user_id=result.get('UserSub'),
            email=request.email
        )
    except Exception as e:
        logger.error(f"Signup error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/auth/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    """Login and get JWT tokens"""
    try:
        result = authenticate_user(request.email, request.password)
        return AuthResponse(
            message="Login successful",
            access_token=result['AuthenticationResult']['AccessToken'],
            id_token=result['AuthenticationResult']['IdToken'],
            refresh_token=result['AuthenticationResult']['RefreshToken'],
            expires_in=result['AuthenticationResult']['ExpiresIn'],
            email=request.email
        )
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )


@app.post("/auth/refresh", response_model=AuthResponse)
async def refresh_token(request: RefreshRequest):
    """Refresh access token"""
    try:
        result = refresh_access_token(request.refresh_token)
        return AuthResponse(
            message="Token refreshed successfully",
            access_token=result['AuthenticationResult']['AccessToken'],
            id_token=result['AuthenticationResult']['IdToken'],
            expires_in=result['AuthenticationResult']['ExpiresIn']
        )
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )


@app.post("/auth/confirm")
async def confirm(request: ConfirmRequest):
    """Confirm user signup with verification code"""
    try:
        confirm_signup(request.email, request.confirmation_code)
        return {"message": "Account verified successfully"}
    except Exception as e:
        logger.error(f"Confirmation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


# Document management endpoints
@app.post("/documents/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    user_info: dict = Depends(get_current_user)
):
    """Upload and index a document"""
    try:
        # Validate file type
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
        # Read file content
        content = await file.read()
        
        # Upload via RAG service
        result = await rag_service.upload_document(
            filename=file.filename,
            content=content,
            user_id=user_info['sub']
        )
        
        return DocumentResponse(
            message="Document uploaded and indexing started",
            document_id=result['document_id'],
            filename=file.filename,
            status=result['status']
        )
        
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/documents")
async def list_documents(user_info: dict = Depends(get_current_user)):
    """List all documents for the current user"""
    try:
        documents = await rag_service.list_documents(user_info['sub'])
        return {"documents": documents, "count": len(documents)}
    except Exception as e:
        logger.error(f"List documents error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/documents/{doc_id}")
async def delete_document(doc_id: str, user_info: dict = Depends(get_current_user)):
    """Delete a document"""
    try:
        success = await rag_service.delete_document(doc_id, user_info['sub'])
        if success:
            return {"message": "Document deleted successfully", "document_id": doc_id}
        else:
            raise HTTPException(status_code=404, detail="Document not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete document error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# RAG query endpoints
@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest, user_info: dict = Depends(get_current_user)):
    """Ask a question using Bedrock Agent"""
    try:
        result = await rag_service.query(
            question=request.question,
            user_id=user_info['sub'],
            session_id=request.session_id
        )
        
        return QueryResponse(
            answer=result['answer'],
            sources=result.get('sources', []),
            session_id=result.get('session_id'),
            trace=result.get('trace')
        )
        
    except Exception as e:
        logger.error(f"Query error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/query/history")
async def query_history(
    limit: int = 10,
    user_info: dict = Depends(get_current_user)
):
    """Get query history for the current user"""
    try:
        history = await rag_service.get_query_history(user_info['sub'], limit)
        return {"history": history, "count": len(history)}
    except Exception as e:
        logger.error(f"Query history error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Frontend ─────────────────────────────
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/")
    async def serve_frontend():
        return FileResponse(str(FRONTEND_DIR / "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.FASTAPI_HOST,
        port=settings.FASTAPI_PORT,
        reload=settings.FASTAPI_DEBUG
    )
