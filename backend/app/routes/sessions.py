from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.services import chat_history as chat_service
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

router = APIRouter()

class MessageRead(BaseModel):
    role: str
    content: str
    sources: Optional[List[str]] = None
    timestamp: datetime

    class Config:
        from_attributes = True

class SessionRead(BaseModel):
    id: str
    title: str
    updated_at: datetime

    class Config:
        from_attributes = True

class SessionDetail(SessionRead):
    messages: List[MessageRead]

@router.get("/sessions", response_model=List[SessionRead])
async def list_sessions(db: AsyncSession = Depends(get_db)):
    """List all chat sessions."""
    return await chat_service.get_all_sessions(db)

@router.get("/sessions/{session_id}", response_model=SessionDetail)
async def get_session(session_id: str, db: AsyncSession = Depends(get_db)):
    """Get a specific session with its messages."""
    session_result = await chat_service.get_all_sessions(db) # This is inefficient but works for now
    # Better: get single session
    from sqlalchemy import select
    from app.db.models import ChatSession
    result = await db.execute(select(ChatSession).where(ChatSession.id == session_id))
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    messages = await chat_service.get_session_messages(db, session_id)
    
    # Process messages to parse sources JSON
    import json
    processed_messages = []
    for msg in messages:
        processed_messages.append({
            "role": msg.role,
            "content": msg.content,
            "sources": json.loads(msg.sources) if msg.sources else [],
            "timestamp": msg.timestamp
        })
        
    return {
        "id": session.id,
        "title": session.title,
        "updated_at": session.updated_at,
        "messages": processed_messages
    }

@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a chat session."""
    await chat_service.delete_session(db, session_id)
    return {"status": "success", "message": "Session deleted"}
