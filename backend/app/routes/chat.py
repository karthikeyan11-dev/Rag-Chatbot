from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.rag_pipeline import get_answer

router = APIRouter()


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
        raise HTTPException(status_code=400, detail="Question is too long. Max 2000 characters.")

    try:
        result = get_answer(question)
        return ChatResponse(answer=result["answer"], sources=result["sources"])
    except Exception as e:
        print(f"Error processing chat request: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while processing your question.")
