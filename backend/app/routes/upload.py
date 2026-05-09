import logging
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException, status, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db, async_session_factory
from app.services.ingest import ingest_documents
from app.services.vector_store import get_collection_size, delete_document_vectors
from app.services.s3_service import s3_service
from app.services import chat_history as chat_service
from app.utils.cache_manager import clear_chat_cache
import asyncio

router = APIRouter()
logger = logging.getLogger(__name__)

# Simple in-memory ingestion status tracker
_ingestion_status = {"status": "idle", "message": "No ingestion in progress."}
_ingestion_lock = False

def _run_ingestion_sync():
    """
    Synchronous wrapper for ingestion. 
    FastAPI runs regular 'def' background tasks in a separate thread pool,
    preventing the event loop from being blocked by heavy CPU/IO RAG tasks.
    """
    global _ingestion_status, _ingestion_lock
    
    if _ingestion_lock:
        return
        
    _ingestion_lock = True
    _ingestion_status = {"status": "processing", "message": "Ingesting documents from AWS S3..."}
    
    try:
        # 1. Clear cache to prevent stale grounded answers
        clear_chat_cache()
        
        # 2. Perform actual synchronous ingestion (Semantic chunking, embeddings, Chroma storage)
        ingest_documents()
        
        # 3. Use an internal event loop to update RDS status (since RDS services are async)
        async def update_status():
            async with async_session_factory() as db:
                docs = await chat_service.get_all_documents(db)
                for doc in docs:
                    if doc.ingestion_status == "pending":
                        await chat_service.update_ingestion_status(db, doc.filename, "completed")
        
        asyncio.run(update_status())
        
        chunk_count = get_collection_size()
        _ingestion_status = {
            "status": "complete",
            "message": f"Ingestion complete. {chunk_count} total semantic chunks indexed."
        }
    except Exception as e:
        logger.error(f"Deep Audit: Background ingestion failed: {e}", exc_info=True)
        _ingestion_status = {"status": "error", "message": f"Ingestion error: {str(e)}"}
        
        async def mark_errors():
            try:
                async with async_session_factory() as db:
                    docs = await chat_service.get_all_documents(db)
                    for doc in docs:
                        if doc.ingestion_status == "pending":
                            await chat_service.update_ingestion_status(db, doc.filename, "error")
            except: pass
        asyncio.run(mark_errors())
    finally:
        _ingestion_lock = False

@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_documents(
    background_tasks: BackgroundTasks, 
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload multiple PDFs to AWS S3 and track in AWS RDS.
    Safety: Prevents blocking the event loop and ensures background persistence.
    """
    saved_files = []
    errors = []

    for file in files:
        if not file.filename.lower().endswith(".pdf"):
            errors.append(f"Skipped '{file.filename}': Invalid file type.")
            continue
        
        try:
            # 1. Purge stale vectors for this filename
            delete_document_vectors(file.filename)
            
            # 2. Real Cloud Upload
            doc_id = str(uuid.uuid4())[:8]
            s3_key = f"company-documents/{doc_id}/{file.filename}"
            
            # Uploading directly from the stream
            success = s3_service.upload_file(file.file, file.filename, document_id=doc_id)
            
            if success:
                # 3. RDS Registration
                await chat_service.register_document(db, file.filename, s3_key, doc_id)
                saved_files.append(file.filename)
                logger.info(f"Audit: Successfully uploaded and registered {file.filename}")
            else:
                errors.append(f"AWS S3 upload failed for '{file.filename}'.")
        except Exception as e:
            logger.error(f"Audit: Upload error for {file.filename}: {e}")
            errors.append(f"Processing error for '{file.filename}'.")

    if not saved_files:
        raise HTTPException(status_code=400, detail=errors[0] if errors else "No files uploaded.")

    # HARDENING: Use a synchronous background task to prevent event loop blocking
    background_tasks.add_task(_run_ingestion_sync)
    
    return {
        "message": "Upload successful. Background ingestion triggered.",
        "files": saved_files,
        "errors": errors,
        "status": "processing"
    }

@router.get("/documents")
async def list_documents(db: AsyncSession = Depends(get_db)):
    """List documents with RDS as the source of truth."""
    try:
        docs = await chat_service.get_all_documents(db)
        chunk_count = get_collection_size()
        return {
            "documents": [d.filename for d in docs],
            "details": [
                {
                    "name": d.filename, 
                    "status": d.ingestion_status, 
                    "date": d.upload_date.isoformat(),
                    "s3_key": d.s3_key
                } for d in docs
            ],
            "total_chunks": chunk_count
        }
    except Exception as e:
        logger.error(f"Audit: List documents error: {e}")
        return {"documents": [], "total_chunks": 0}

@router.delete("/documents/{filename:path}")
async def delete_document(filename: str, db: AsyncSession = Depends(get_db)):
    """
    Hardened synchronized deletion with atomic-like behavior.
    """
    logger.info(f"Audit: Critical deletion request for '{filename}'")
    
    # 1. Check if it exists in RDS first
    from sqlalchemy import select
    from app.db.models import DocumentMetadata
    result = await db.execute(select(DocumentMetadata).where(DocumentMetadata.filename == filename))
    doc_metadata = result.scalar_one_or_none()
    
    if not doc_metadata:
        # Check ChromaDB anyway as a safety measure for orphaned vectors
        delete_document_vectors(filename)
        return {"message": "Document record not found, but vectors purged if any.", "status": "partial"}

    # 2. Cloud Purge
    results = {"s3": False, "chroma": False, "rds": False}
    
    try:
        results["s3"] = s3_service.delete_file(filename)
    except Exception as e:
        logger.error(f"Audit: S3 Deletion Error: {e}")

    try:
        results["chroma"] = delete_document_vectors(filename)
    except Exception as e:
        logger.error(f"Audit: Chroma Deletion Error: {e}")

    try:
        await chat_service.delete_document_metadata(db, filename)
        results["rds"] = True
    except Exception as e:
        logger.error(f"Audit: RDS Deletion Error: {e}")

    clear_chat_cache()
    return {"message": "Synchronized deletion completed.", "results": results}

@router.get("/ingestion-status")
async def ingestion_status():
    return _ingestion_status
