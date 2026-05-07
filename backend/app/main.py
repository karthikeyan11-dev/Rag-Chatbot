from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.routes.chat import router as chat_router
from app.services.ingest import ingest_documents


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run ingestion on startup."""
    print("Starting RAG chatbot backend...")
    ingest_documents()
    print("Ingestion complete. Backend ready.")
    yield


app = FastAPI(
    title="RAG Chatbot API",
    description="Company Policy RAG Chatbot powered by LangChain + ChromaDB",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix="/api")


@app.get("/")
def health_check():
    return {"status": "ok", "message": "RAG Chatbot API is running"}
