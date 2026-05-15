import json
from datetime import datetime
from sqlalchemy import select, delete, desc, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import ChatSession, ChatMessage, DocumentMetadata

# --- Session & Message Services ---

async def create_session(db: AsyncSession, session_id: str, title: str = "New Chat", user_id: int = None):
    """Create a new chat session."""
    session = ChatSession(id=session_id, title=title, user_id=user_id)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session

async def get_all_sessions(db: AsyncSession, user_id: int = None):
    """Get all chat sessions for a specific user ordered by updated_at."""
    stmt = select(ChatSession)
    if user_id is not None:
        stmt = stmt.where(ChatSession.user_id == user_id)
    
    result = await db.execute(stmt.order_by(desc(ChatSession.updated_at)))
    return result.scalars().all()

async def get_session_messages(db: AsyncSession, session_id: str):
    """Get all messages for a specific session."""
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.timestamp)
    )
    return result.scalars().all()

async def add_message(db: AsyncSession, session_id: str, role: str, content: str, sources: list = None):
    """Add a message to a session and update the session's timestamp."""
    # Fetch session explicitly to avoid lazy-loading issues in async context
    session_result = await db.execute(select(ChatSession).where(ChatSession.id == session_id))
    session = session_result.scalar_one_or_none()
    
    if not session:
        return None

    message = ChatMessage(
        session_id=session_id,
        role=role,
        content=content,
        sources=json.dumps(sources) if sources else None
    )
    db.add(message)
    
    session.updated_at = datetime.utcnow()
    
    # Update title if it's the first user message
    if role == "user":
        # Check message count without relying on lazy relationships
        count_result = await db.execute(
            select(func.count(ChatMessage.id)).where(ChatMessage.session_id == session_id)
        )
        msg_count = count_result.scalar()
        if msg_count == 0: # This is the first message (not yet committed)
            session.title = content[:40] + ("..." if len(content) > 40 else "")

    await db.commit()
    return message

async def delete_session(db: AsyncSession, session_id: str):
    """Delete a chat session and all its messages."""
    await db.execute(delete(ChatSession).where(ChatSession.id == session_id))
    await db.commit()

# --- Document Metadata Services (Hardening) ---

async def register_document(db: AsyncSession, filename: str, s3_key: str, document_id: str, user_id: int):
    """Register or update document metadata in RDS with user ownership."""
    # Check if exists for THIS user
    result = await db.execute(
        select(DocumentMetadata)
        .where(DocumentMetadata.filename == filename)
        .where(DocumentMetadata.user_id == user_id)
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        existing.s3_key = s3_key
        existing.document_id = document_id
        existing.upload_date = datetime.utcnow()
        existing.ingestion_status = "pending"
    else:
        new_doc = DocumentMetadata(
            filename=filename,
            s3_key=s3_key,
            document_id=document_id,
            user_id=user_id
        )
        db.add(new_doc)
    
    await db.commit()

async def get_all_documents(db: AsyncSession, user_id: int = None):
    """List documents belonging to a specific user from RDS metadata."""
    stmt = select(DocumentMetadata)
    if user_id is not None:
        stmt = stmt.where(DocumentMetadata.user_id == user_id)
        
    result = await db.execute(stmt.order_by(desc(DocumentMetadata.upload_date)))
    return result.scalars().all()

async def delete_document_metadata(db: AsyncSession, filename: str, user_id: int):
    """Remove document metadata from RDS for a specific user."""
    await db.execute(
        delete(DocumentMetadata)
        .where(DocumentMetadata.filename == filename)
        .where(DocumentMetadata.user_id == user_id)
    )
    await db.commit()

async def get_document_by_name(db: AsyncSession, filename: str, user_id: int):
    """Get metadata for a specific document belonging to a user."""
    result = await db.execute(
        select(DocumentMetadata)
        .where(DocumentMetadata.filename == filename)
        .where(DocumentMetadata.user_id == user_id)
    )
    return result.scalar_one_or_none()

async def update_ingestion_status(db: AsyncSession, filename: str, status: str, user_id: int):
    """Update ingestion status for a user's document."""
    await db.execute(
        update(DocumentMetadata)
        .where(DocumentMetadata.filename == filename)
        .where(DocumentMetadata.user_id == user_id)
        .values(ingestion_status=status)
    )
    await db.commit()
