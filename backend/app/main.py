import asyncio
import sys
import os
from dotenv import load_dotenv

# Pre-load environment variables to ensure they are available before imports
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
load_dotenv(dotenv_path)

# Windows-specific fix for Psycopg/SQLAlchemy async
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import logging
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import threading
import time

from app.routes.chat import router as chat_router
from app.routes.upload import router as upload_router
from app.routes.sessions import router as sessions_router
from app.db.database import init_db, engine

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info('Starting Cloud-Native RAG chatbot...')
    try:
        await init_db()
        logger.info('Database initialized successfully.')
    except Exception as e:
        logger.error(f'DB Initialization failure: {e}')
    
    def startup_ingest():
        time.sleep(30)
        try:
            from app.services.ingest import ingest_documents
            ingest_documents()
        except Exception as e:
            logger.error(f'Startup ingestion error: {e}')

    thread = threading.Thread(target=startup_ingest, daemon=True)
    thread.start()
    yield
    logger.info('Shutting down RAG chatbot. Cleaning up resources...')
    try:
        await engine.dispose()
        logger.info('Database connections disposed successfully.')
    except Exception as e:
        logger.error(f'Error during engine disposal: {e}')

app = FastAPI(
    title='RAG Chatbot API',
    description='Hardened Cloud-Native Company Policy Assistant',
    version='1.1.0',
    lifespan=lifespan,
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f'Unhandled Exception: {exc}', exc_info=True)
    return JSONResponse(
        status_code=500,
        content={'detail': 'Internal Server Error', 'error': str(exc)}
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        'http://localhost:5173',
        'http://localhost:5174',
        'http://127.0.0.1:5173',
        'http://127.0.0.1:5174',
    ],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(chat_router, prefix='/api')
app.include_router(upload_router, prefix='/api')
app.include_router(sessions_router, prefix='/api')

@app.get('/')
def health_check():
    return {'status': 'healthy', 'service': 'RAG-Chatbot'}

if __name__ == '__main__':
    uvicorn.run('app.main:app', host='127.0.0.1', port=8000, reload=True)
