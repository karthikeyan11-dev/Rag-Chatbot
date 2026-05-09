import json
from datetime import datetime
from sqlalchemy import select, delete, desc, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import ChatSession, ChatMessage, DocumentMetadata

# --- Session & Message Services ---

async def create_session(db: AsyncSession, session_id: str, title: str = "New Chat"):
    """Create a new chat session."""
    session = ChatSession(id=session_id, title=title)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session

async def get_all_sessions(db: AsyncSession):
    """Get all chat sessions ordered by updated_at."""
    result = await db.execute(
        select(ChatSession).order_by(desc(ChatSession.updated_at))
    )
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
    message = ChatMessage(
        session_id=session_id,
        role=role,
        content=content,
        sources=json.dumps(sources) if sources else None
    )
    db.add(message)
    
    # Update session's updated_at timestamp
    session_result = await db.execute(select(ChatSession).where(ChatSession.id == session_id))
    session = session_result.scalar_one_or_none()
    if session:
        session.updated_at = datetime.utcnow()
        # If it's the first user message, update the title
        if role == "user":
            # Check message count
            msg_count_result = await db.execute(
                select(ChatMessage).where(ChatMessage.session_id == session_id)
            )
            if len(msg_count_result.scalars().all()) <= 1:
                session.title = content[:40] + ("..." if len(content) > 40 else "")

    await db.commit()
    return message

async def delete_session(db: AsyncSession, session_id: str):
    """Delete a chat session and all its messages."""
    await db.execute(delete(ChatSession).where(ChatSession.id == session_id))
    await db.commit()

# --- Document Metadata Services (Hardening) ---

async def register_document(db: AsyncSession, filename: str, s3_key: str, document_id: str):
    """Register or update document metadata in RDS."""
    # Check if exists
    result = await db.execute(select(DocumentMetadata).where(DocumentMetadata.filename == filename))
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
            document_id=document_id
        )
        db.add(new_doc)
    
    await db.commit()

async def update_ingestion_status(db: AsyncSession, filename: str, status: str):
    """Update the ingestion status of a document."""
    await db.execute(
        update(DocumentMetadata)
        .where(DocumentMetadata.filename == filename)
        .values(ingestion_status=status)
    )
    await db.commit()

async def get_all_documents(db: AsyncSession):
    """List all documents from RDS metadata."""
    result = await db.execute(select(DocumentMetadata).order_by(DocumentMetadata.upload_date))
    return result.scalars().all()

async def delete_document_metadata(db: AsyncSession, filename: str):
    """Remove document metadata from RDS."""
    await db.execute(delete(DocumentMetadata).where(DocumentMetadata.filename == filename))
    await db.commit()
