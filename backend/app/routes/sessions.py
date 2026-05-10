from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.db.models import ChatSession, ChatMessage, User
from app.services import chat_history as chat_service
from app.utils.auth_deps import get_current_user
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from sqlalchemy import select

router = APIRouter(tags=["Chat Sessions"])

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
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List current user's chat sessions."""
    return await chat_service.get_all_sessions(db, user_id=current_user.id)

@router.get("/sessions/{session_id}", response_model=SessionDetail)
async def get_session(
    session_id: str, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific session with its messages, ensuring ownership."""
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.id == session_id)
        .where(ChatSession.user_id == current_user.id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or unauthorized")
        
    messages = await chat_service.get_session_messages(db, session_id)
    return {
        "id": session.id,
        "title": session.title,
        "updated_at": session.updated_at,
        "messages": messages
    }

    
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
async def delete_session(
    session_id: str, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a chat session with ownership check."""
    from sqlalchemy import delete
    # Verify ownership
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.id == session_id)
        .where(ChatSession.user_id == current_user.id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or unauthorized")

    await db.execute(delete(ChatMessage).where(ChatMessage.session_id == session_id))
    await db.execute(delete(ChatSession).where(ChatSession.id == session_id))
    await db.commit()
    return {"status": "success", "message": "Session deleted"}
