import os
import shutil
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException, status, BackgroundTasks
from app.services.ingest import ingest_documents
from app.services.vector_store import get_collection_size, delete_document_vectors
from app.utils.cache_manager import clear_chat_cache

router = APIRouter()
logger = logging.getLogger(__name__)

# Resolve the absolute path for the PDF storage directory
PDF_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "pdfs")
PDF_DIR = os.path.abspath(PDF_DIR)

# Simple in-memory ingestion status tracker
_ingestion_status = {"status": "idle", "message": "No ingestion in progress."}
_ingestion_lock = False # Simple flag to prevent concurrent ingestion tasks

def _run_ingestion():
    """Wrapper to run ingestion and track its status."""
    global _ingestion_status, _ingestion_lock
    
    if _ingestion_lock:
        logger.info("Ingestion already in progress. Skipping duplicate task.")
        return
        
    _ingestion_lock = True
    _ingestion_status = {"status": "processing", "message": "Ingesting documents... This may take a minute."}
    try:
        # Clear chat cache before starting to ensure no stale answers during ingestion
        clear_chat_cache()
        ingest_documents()
        chunk_count = get_collection_size()
        _ingestion_status = {
            "status": "complete",
            "message": f"Ingestion complete. {chunk_count} total chunks in database."
        }
    except Exception as e:
        logger.error(f"Background ingestion failed: {e}")
        _ingestion_status = {
            "status": "error",
            "message": f"Ingestion encountered an error: {str(e)}"
        }
    finally:
        _ingestion_lock = False

@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_documents(background_tasks: BackgroundTasks, files: list[UploadFile] = File(...)):
    """
    Upload multiple PDFs and trigger the ingestion pipeline.
    
    This endpoint:
    1. Saves the uploaded files to the data directory.
    2. Returns an immediate response to the client.
    3. Triggers the heavy RAG ingestion pipeline (parsing, chunking, embedding) 
       as a FastAPI BackgroundTask to avoid HTTP timeouts.
    """
    if not os.path.exists(PDF_DIR):
        os.makedirs(PDF_DIR, exist_ok=True)

    saved_files = []
    errors = []

    for file in files:
        # Validate file type
        if not file.filename.lower().endswith(".pdf"):
            errors.append(f"Skipped '{file.filename}': Only PDF files are allowed.")
            continue
        
        # Validate file size (max 50MB)
        file_content = await file.read()
        if len(file_content) > 50 * 1024 * 1024:
            errors.append(f"Skipped '{file.filename}': File exceeds 50MB size limit.")
            continue
        
        # Validate file is not empty
        if len(file_content) == 0:
            errors.append(f"Skipped '{file.filename}': File is empty.")
            continue
        
        file_path = os.path.join(PDF_DIR, file.filename)
        
        try:
            # FIX: If file already exists, we must delete its old vectors first
            # to ensure the ingestion pipeline sees it as "new" and re-indexes it.
            if os.path.exists(file_path):
                logger.info(f"File '{file.filename}' already exists. Purging old vectors for re-indexing.")
                delete_document_vectors(file.filename)
            
            with open(file_path, "wb") as buffer:
                buffer.write(file_content)
            saved_files.append(file.filename)
            logger.info(f"Saved uploaded file: {file.filename} ({len(file_content)} bytes)")
        except Exception as e:
            logger.error(f"Error saving file {file.filename}: {e}")
            errors.append(f"Failed to save '{file.filename}': The file could not be written to disk.")
            continue

    # If no files were successfully saved, return an error
    if not saved_files:
        detail = errors[0] if errors else "No valid PDF files were provided in the upload."
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    # Trigger ingestion as a BackgroundTask
    try:
        background_tasks.add_task(_run_ingestion)
        logger.info(f"Scheduled background ingestion for: {saved_files}")
    except Exception as e:
        logger.error(f"Failed to schedule background task: {e}")

    return {
        "message": f"Successfully uploaded {len(saved_files)} file(s). Ingestion is processing in the background.",
        "files": saved_files,
        "errors": errors,
        "status": "processing"
    }

@router.get("/documents")
async def list_documents():
    """
    List all PDF documents currently stored in the system.
    """
    if not os.path.exists(PDF_DIR):
        return {"documents": [], "total_chunks": 0}
    
    try:
        files = [f for f in os.listdir(PDF_DIR) if f.lower().endswith(".pdf")]
        files.sort()
        chunk_count = get_collection_size()
        return {"documents": files, "total_chunks": chunk_count}
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        return {"documents": [], "total_chunks": 0, "error": "Could not retrieve document list."}

@router.delete("/documents/{filename:path}")
async def delete_document(filename: str):
    """
    Delete a document and all its related vectors/embeddings.
    """
    logger.info(f"Deletion request received for filename: '{filename}'")
    file_path = os.path.join(PDF_DIR, filename)
    logger.info(f"Target file path for deletion: '{file_path}'")
    
    # 1. Check if file exists on disk
    if not os.path.exists(file_path):
        logger.warning(f"Deletion failed: Document '{filename}' not found on disk.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="The document could not be deleted because it was not found."
        )

    try:
        # 2. Remove physical PDF file
        os.remove(file_path)
        logger.info(f"Deleted PDF file from disk: {filename}")
        
        # 3. Remove related vectors from ChromaDB
        success = delete_document_vectors(filename)
        
        # Clear chat cache as the knowledge base has changed
        clear_chat_cache()
        
        if not success:
            logger.error(f"Database sync failed: Could not remove embeddings for {filename}")
            # We still return success for the file but warn about the DB
            return {
                "message": "Document file removed, but failed to remove document embeddings from ChromaDB. Database may be out of sync.",
                "status": "partial_success"
            }

        return {
            "message": "Document deleted successfully.",
            "status": "success",
            "filename": filename
        }
    except Exception as e:
        logger.error(f"Critical error during deletion of {filename}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while deleting the document: {str(e)}"
        )

@router.get("/ingestion-status")
async def ingestion_status():
    """Return the current status of the background ingestion pipeline."""
    return _ingestion_status
