from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

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
