import logging
import uuid
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.services.rag_pipeline import get_answer
from app.services import chat_history as chat_service
from typing import Optional, List

router = APIRouter()
logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    question: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[str]
    session_id: str


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    question = request.question.strip()

    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    if len(question) > 2000:
        raise HTTPException(status_code=400, detail="Question is too long. Please limit to 2000 characters.")

    # Get or create session ID
    session_id = request.session_id
    if not session_id:
        session_id = str(uuid.uuid4())
        await chat_service.create_session(db, session_id)
        logger.info(f"Created new chat session: {session_id}")
    else:
        # Verify session exists
        from sqlalchemy import select
        from app.db.models import ChatSession
        result = await db.execute(select(ChatSession).where(ChatSession.id == session_id))
        if not result.scalar_one_or_none():
            # If session ID provided but not found, create it (robustness)
            await chat_service.create_session(db, session_id)
            logger.info(f"Re-created missing session: {session_id}")

    try:
        logger.info(f"Chat request received for session {session_id}: '{question[:80]}...'")
        
        # 1. Save user message to database
        await chat_service.add_message(db, session_id, "user", question)
        
        # 2. Get previous messages for context
        history = await chat_service.get_session_messages(db, session_id)
        # Pass history to RAG pipeline (excluding the current user message which was just added)
        # Or just pass the last N messages
        chat_history_context = []
        for msg in history[:-1]: # Exclude the one we just added to avoid duplication in pipeline logic if any
             chat_history_context.append({"role": msg.role, "content": msg.content})

        # 3. Generate Answer via RAG Pipeline
        result = get_answer(question, chat_history=chat_history_context)
        
        # 4. Save assistant response to database
        await chat_service.add_message(
            db, 
            session_id, 
            "assistant", 
            result["answer"], 
            sources=result["sources"]
        )
        
        return ChatResponse(
            answer=result["answer"], 
            sources=result["sources"],
            session_id=session_id
        )
    except Exception as e:
        logger.error(f"Error processing chat request: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while processing your question. Please try again."
        )
