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

from app.utils.auth_deps import get_current_user
from app.db.models import User, DocumentMetadata
from sqlalchemy import select

router = APIRouter(tags=["Document Management"])
logger = logging.getLogger(__name__)

# Simple in-memory ingestion status tracker
_ingestion_status = {"status": "idle", "message": "No ingestion in progress."}
_ingestion_lock = False

async def _run_ingestion_sync():
    """
    Background worker for ingestion.
    Note: Always run the async ingestion in its own thread to avoid event loop conflicts.
    """
    global _ingestion_status, _ingestion_lock
    
    if _ingestion_lock:
        logger.info("Ingestion lock active, skipping redundant trigger.")
        return
        
    _ingestion_lock = True
    _ingestion_status = {"status": "processing", "message": "Synchronizing storage systems..."}
    
    try:
        # HARDENING: Defensive sleep to ensure RDS commits are visible (RDS Propagation Delay)
        await asyncio.sleep(1)
        
        # 1. Clear cache
        clear_chat_cache()
        
        # 2. Perform actual ingestion
        from app.services.ingest import ingest_documents
        
        # We run the async ingestion directly since uvicorn/fastapi handles the loop.
        await ingest_documents()
        
        _ingestion_status = {
            "status": "complete",
            "message": "Cloud-native synchronization successful."
        }
    except Exception as e:
        logger.error(f"Ingestion worker failed: {e}", exc_info=True)
        _ingestion_status = {"status": "error", "message": f"Sync error: {str(e)}"}
    finally:
        _ingestion_lock = False

@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_documents(
    background_tasks: BackgroundTasks, 
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    STRICTLY USER-SCOPED: Upload multiple PDFs to AWS S3 and track in RDS.
    Transferred to structure: users/{user_id}/documents/{document_id}/{filename}
    Includes atomicity hardening with rollback logic.
    """
    saved_files = []
    errors = []

    for file in files:
        if not file.filename.lower().endswith(".pdf"):
            errors.append(f"Skipped '{file.filename}': Invalid file type (Only PDF allowed).")
            continue
        
        s3_key = None
        doc_id = str(uuid.uuid4())[:8]
        
        try:
            # 1. Clean existing state for this file if user re-uploads
            from app.services.vector_store import delete_document_vectors
            delete_document_vectors(file.filename, user_id=current_user.id)
            
            # 2. S3 Upload - Returns standard user-scoped key
            s3_key = s3_service.upload_file(
                file.file, 
                file.filename, 
                user_id=current_user.id, 
                document_id=doc_id
            )
            
            if not s3_key:
                raise Exception("S3 Upload Failed")

            # 3. RDS Registration
            await chat_service.register_document(
                db, 
                filename=file.filename, 
                s3_key=s3_key, 
                document_id=doc_id, 
                user_id=current_user.id
            )
            saved_files.append(file.filename)
            logger.info(f"STRICT: Uploaded & Registered {file.filename} for User {current_user.id}")

        except Exception as e:
            logger.error(f"Atomic Upload Error for {file.filename}: {e}")
            # Rollback S3 if RDS registration failed
            if s3_key:
                logger.warning(f"ROLLBACK: Deleting orphaned S3 object {s3_key}")
                s3_service.delete_object(s3_key)
            
            errors.append(f"Processing error for '{file.filename}': {str(e)}")

    if not saved_files:
        raise HTTPException(status_code=400, detail=errors[0] if errors else "No files processed.")

    # Trigger background ingestion
    background_tasks.add_task(_run_ingestion_sync)
    
    return {
        "message": "Upload successful. Ingestion started.",
        "files": saved_files,
        "errors": errors
    }

@router.delete("/documents/{filename}")
async def delete_document(
    filename: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """STRICTLY USER-SCOPED: Synchronized deletion from S3, RDS, and Chroma."""
    try:
        # 1. Get metadata from RDS first to get S3 key
        doc = await chat_service.get_document_by_name(db, filename, current_user.id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found.")

        # 2. Delete from Chroma vectors
        from app.services.vector_store import delete_document_vectors
        delete_document_vectors(filename, user_id=current_user.id)

        # 3. Delete from S3
        s3_service.delete_object(doc.s3_key)

        # 4. Delete from RDS
        await chat_service.delete_document_metadata(db, filename, current_user.id)

        # 5. Clear chat cache
        clear_chat_cache()

        return {"message": f"Successfully deleted {filename}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete failed: {e}")
        raise HTTPException(status_code=500, detail=f"Deletion error: {str(e)}")

@router.get("/documents")
async def list_documents(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List documents belonging to the current user."""
    try:
        docs = await chat_service.get_all_documents(db, user_id=current_user.id)
        return {
            "documents": [d.filename for d in docs],
            "details": [
                {
                    "name": d.filename, 
                    "status": d.ingestion_status, 
                    "date": d.upload_date.isoformat(),
                    "s3_key": d.s3_key
                } for d in docs
            ]
        }
    except Exception as e:
        logger.error(f"Audit: List documents error: {e}")
        return {"documents": []}

@router.get("/ingestion-status")
async def ingestion_status():
    return _ingestion_status
