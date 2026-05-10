import logging
import uuid
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.db.models import User, ChatSession
from app.services.rag_pipeline import get_answer
from app.services import chat_history as chat_service
from app.utils.auth_deps import get_current_user
from typing import Optional, List
from sqlalchemy import select

router = APIRouter(tags=["Chat"])
logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    question: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[str]
    session_id: str


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    question = request.question.strip()

    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    if len(question) > 2000:
        raise HTTPException(status_code=400, detail="Question is too long. Please limit to 2000 characters.")

    # Get or create session ID
    session_id = request.session_id
    if not session_id:
        session_id = str(uuid.uuid4())
        await chat_service.create_session(db, session_id, user_id=current_user.id)
        logger.info(f"Created new chat session: {session_id} for user {current_user.id}")
    else:
        # Verify session exists and belongs to user
        result = await db.execute(
            select(ChatSession)
            .where(ChatSession.id == session_id)
            .where(ChatSession.user_id == current_user.id)
        )
        if not result.scalar_one_or_none():
            # If session ID provided but not found/authorized, create new for THIS user
            # Alternatively, reject. We'll create for user isolation.
            session_id = str(uuid.uuid4())
            await chat_service.create_session(db, session_id, user_id=current_user.id)
            logger.info(f"Created new session (prev invalid): {session_id} for user {current_user.id}")


    try:
        logger.info(f"Chat request received for session {session_id}: '{question[:80]}...'")
        
        # 1. Save user message to database
        await chat_service.add_message(db, session_id, "user", question)
        
        # 2. Get previous messages for context
        history = await chat_service.get_session_messages(db, session_id)
        
        # Pass history to RAG pipeline (excluding current user message which is history[-1])
        chat_history_context = []
        for msg in history[:-1]:
            chat_history_context.append({"role": msg.role, "content": msg.content})

        # 3. Generate Answer via RAG Pipeline (Scoped to current user)
        # Audit: updated get_answer to be async/thread-safe
        result = await get_answer(question, chat_history=chat_history_context, user_id=current_user.id)
        
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
