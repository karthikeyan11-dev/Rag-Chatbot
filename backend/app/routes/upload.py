import os
import shutil
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from app.services.ingest import ingest_documents

router = APIRouter()
logger = logging.getLogger(__name__)

PDF_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "pdfs")
PDF_DIR = os.path.abspath(PDF_DIR)

@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_documents(files: list[UploadFile] = File(...)):
    """
    Upload multiple PDFs and trigger the ingestion pipeline.
    Validates file types and handles storage.
    """
    if not os.path.exists(PDF_DIR):
        os.makedirs(PDF_DIR, exist_ok=True)

    saved_files = []
    errors = []

    for file in files:
        if not file.filename.lower().endswith(".pdf"):
            errors.append(f"Skipped {file.filename}: Only PDF files are allowed.")
            continue
        
        file_path = os.path.join(PDF_DIR, file.filename)
        
        try:
            # Using with statement ensures the file is closed properly
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            saved_files.append(file.filename)
        except Exception as e:
            logger.error(f"Error saving file {file.filename}: {e}")
            errors.append(f"Failed to save {file.filename}")
            continue

    if not saved_files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=errors[0] if errors else "No valid PDF files uploaded"
        )

    # Trigger ingestion pipeline
    try:
        logger.info(f"Triggering ingestion for {len(saved_files)} files...")
        ingest_documents()
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        # We still return 201 because files were saved, but with a warning
        return {
            "message": "Files uploaded successfully, but background ingestion failed. Please contact support.",
            "files": saved_files,
            "errors": errors,
            "status": "partial_success"
        }

    return {
        "message": f"Successfully uploaded and ingested {len(saved_files)} file(s)",
        "files": saved_files,
        "errors": errors,
        "status": "success"
    }

@router.get("/documents")
async def list_documents():
    """List all processed documents available in the RAG system."""
    if not os.path.exists(PDF_DIR):
        return {"documents": []}
    
    files = [f for f in os.listdir(PDF_DIR) if f.lower().endswith(".pdf")]
    # Sort files by name for consistent UI display
    files.sort()
    return {"documents": files}

