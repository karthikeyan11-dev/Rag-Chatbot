import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.routes.chat import router as chat_router
from app.routes.upload import router as upload_router
from app.services.ingest import ingest_documents

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

import threading
import time

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run initial ingestion on startup in a background thread with a delay."""
    logger.info("Starting RAG chatbot backend (ChromaDB)...")
    
    # Startup Ingestion (Incremental) - Run in background with a delay
    def startup_ingest():
        # Wait 60 seconds to give the user quota priority on startup
        time.sleep(60)
        try:
            from app.services.ingest import ingest_documents
            ingest_documents()
            logger.info("Startup ingestion complete.")
        except Exception as e:
            logger.error(f"Startup ingestion error: {e}")

    thread = threading.Thread(target=startup_ingest)
    thread.start()
    
    yield

app = FastAPI(
    title="RAG Chatbot API",
    description="Company Policy RAG Chatbot powered by LangChain + ChromaDB + Google Gemini",
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
app.include_router(upload_router, prefix="/api")

@app.get("/")
def health_check():
    return {"status": "ok", "message": "RAG Chatbot API is running with local ChromaDB persistence"}
