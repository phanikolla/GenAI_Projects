"""
Pydantic models for API requests and responses
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr


# Authentication models
class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class ConfirmRequest(BaseModel):
    email: EmailStr
    confirmation_code: str


class AuthResponse(BaseModel):
    message: str
    access_token: Optional[str] = None
    id_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None
    user_id: Optional[str] = None
    email: Optional[str] = None


# Document models
class DocumentResponse(BaseModel):
    message: str
    document_id: str
    filename: str
    status: str


# Query models
class QueryRequest(BaseModel):
    question: str
    session_id: Optional[str] = None


class QueryResponse(BaseModel):
    answer: str
    sources: Optional[List[Dict[str, Any]]] = []
    session_id: Optional[str] = None
    trace: Optional[Dict[str, Any]] = None
