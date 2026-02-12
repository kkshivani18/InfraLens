from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class User(BaseModel):
    """User document with GitHub integration"""
    user_id: str 
    email: Optional[str] = None
    github_token: Optional[str] = None
    github_username: Optional[str] = None
    connected_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Message(BaseModel):
    """single chat message"""
    role: str 
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class Chat(BaseModel):
    """Chat conversation document"""
    user_id: str
    repository_name: Optional[str] = None 
    messages: List[Message] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class Repository(BaseModel):
    """Repository document"""
    user_id: str
    github_url: str
    name: str  
    collection_name: str  
    is_private: bool = False  
    files_processed: int = 0
    chunks_stored: int = 0
    ingested_at: datetime = Field(default_factory=datetime.utcnow)

class ChatRequest(BaseModel):
    """Chat API request"""
    message: str
    repository_name: Optional[str] = None

class IngestRequest(BaseModel):
    """Repository ingestion API request"""
    repo_url: str

class GitHubConnectRequest(BaseModel):
    """GitHub OAuth connection request"""
    github_token: str
    github_username: Optional[str] = None
