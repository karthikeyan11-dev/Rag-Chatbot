import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.rag_pipeline import get_answer

router = APIRouter()
logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    question: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[str]


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    question = request.question.strip()

    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    if len(question) > 2000:
        raise HTTPException(status_code=400, detail="Question is too long. Please limit to 2000 characters.")

    try:
        logger.info(f"Chat request received: '{question[:80]}...'")
        result = get_answer(question)
        return ChatResponse(answer=result["answer"], sources=result["sources"])
    except Exception as e:
        logger.error(f"Error processing chat request: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while processing your question. Please try again."
        )
