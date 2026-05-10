import os
import fitz  # PyMuPDF
import time
import uuid
import logging
import asyncio
from langchain_experimental.text_splitter import SemanticChunker
from app.services.vector_store import get_vector_store
from app.services.s3_service import s3_service
from app.utils.cache_manager import clear_chat_cache
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from sqlalchemy import select, update
from app.db.database import async_session_factory
from app.db.models import DocumentMetadata

# Configure logging
logger = logging.getLogger(__name__)

def clean_text(text: str) -> str:
    """Perform text cleaning to improve embedding quality."""
    import re
    # Remove excessive whitespace and non-printable characters
    text = re.sub(r'\s+', ' ', text)
    text = "".join(ch for ch in text if ch.isprintable())
    return text.strip()


def extract_text_from_s3_pdf(filename: str, user_id: int = None) -> list[dict]:
    """
    Download PDF from S3 and extract text. Hardened for memory and connection safety.
    """
    pages = []
    file_stream = None
    doc = None
    try:
        # User isolation: use user-specific path in S3 if possible, 
        # but s3_service uses full path/key usually.
        # We'll assume 'filename' passed here is actually the S3 Key.
        file_stream = s3_service.get_file_content(filename)
        if not file_stream:
            logger.error(f"S3: Failed to retrieve content for {filename}")
            return []

        doc = fitz.open(stream=file_stream, filetype="pdf")
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text")
            cleaned_text = clean_text(text)
            if cleaned_text:
                pages.append({
                    "text": cleaned_text,
                    "page": page_num + 1,
                    "source": os.path.basename(filename),
                    "user_id": user_id
                })
        
        logger.info(f"PyMuPDF: Extracted {len(pages)} pages from {filename} for user {user_id}")
    except Exception as e:
        logger.error(f"Extraction error for {filename}: {e}")
    finally:
        # HARDENING: Explicitly close resources
        if doc:
            doc.close()
        if file_stream:
            file_stream.close()
    return pages


def chunk_pages_semantically(pages: list[dict]) -> list[dict]:
    """Chunk extracted pages using SemanticChunker with enhanced metadata."""
    if not pages:
        return []
        
    try:
        embeddings = GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-2",
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            task_type="retrieval_document"
        )
        logger.info(f"Chunking: Starting semantic chunking for {len(pages)} pages")
        splitter = SemanticChunker(embeddings, breakpoint_threshold_type="percentile")
        
        chunks = []
        for i, page_data in enumerate(pages):
            logger.info(f"Chunking: Processing page {i+1}/{len(pages)}")
            text_chunks = splitter.split_text(page_data["text"])
            for idx, chunk in enumerate(text_chunks):
                content = chunk.strip()
                if not content: continue
                
                # HARDENING: Richer metadata for cloud traceability and user isolation
                chunks.append({
                    "text": content,
                    "metadata": {
                        "source": page_data["source"],
                        "page": page_data["page"],
                        "chunk_index": idx,
                        "ingested_at": str(time.time()),
                        "user_id": int(page_data.get("user_id")) if page_data.get("user_id") is not None else -1
                    },
                })
        return chunks
    except Exception as e:
        logger.error(f"Semantic Chunking failed: {e}")
        return []


def is_document_indexed(filename: str) -> bool:
    """Check if a document is already indexed in ChromaDB."""
    try:
        vector_store = get_vector_store()
        if vector_store is None: return False
        # Metadata filtering is robust across Chroma restarts
        # Chroma .get() is blocking but this function is sync.
        results = vector_store._collection.get(where={"source": filename}, limit=1)
        return len(results["ids"]) > 0
    except Exception as e:
        logger.error(f"Index check error: {e}")
        return False


async def ingest_documents():
    """Detects documents in RDS with 'pending' status and adds them to ChromaDB. Hardened for multi-tenancy."""
    async with async_session_factory() as db:
        result = await db.execute(
            select(DocumentMetadata).where(DocumentMetadata.ingestion_status == "pending")
        )
        pending_docs = result.scalars().all()

    if not pending_docs:
        logger.info("No pending documents for ingestion.")
        return

    logger.info(f"Ingesting {len(pending_docs)} pending documents.")

    for doc_meta in pending_docs:
        filename = doc_meta.filename
        s3_key = doc_meta.s3_key
        user_id = doc_meta.user_id
        
        try:
            # Mark as processing
            async with async_session_factory() as db:
                await db.execute(
                    update(DocumentMetadata)
                    .where(DocumentMetadata.id == doc_meta.id)
                    .values(ingestion_status="processing")
                )
                await db.commit()

            pages = extract_text_from_s3_pdf(s3_key, user_id=user_id)
            if not pages: 
                 # Mark as error if no pages extracted
                async with async_session_factory() as db:
                    await db.execute(update(DocumentMetadata).where(DocumentMetadata.id == doc_meta.id).values(ingestion_status="error"))
                    await db.commit()
                continue

            chunks = chunk_pages_semantically(pages)
            if not chunks: continue

            vector_store = get_vector_store()
            if vector_store is None: continue

            texts = []
            metadatas = []
            ids = []

            for c in chunks:
                # Grounded content prefixing
                enriched_text = f"Document: {c['metadata']['source']}\nPage: {c['metadata']['page']}\nContent: {c['text']}"
                texts.append(enriched_text)
                metadatas.append(c["metadata"])
                
                # Deterministic ID for idempotency (include user_id for safety)
                uid_string = f"u{user_id}_{c['metadata']['source']}__p{c['metadata']['page']}__c{c['metadata']['chunk_index']}"
                ids.append(str(uuid.uuid5(uuid.NAMESPACE_DNS, uid_string)))

            # HARDENING: Safe batching
            BATCH_SIZE = 10
            for i in range(0, len(texts), BATCH_SIZE):
                await asyncio.to_thread(
                    vector_store.add_texts,
                    texts=texts[i:i + BATCH_SIZE],
                    metadatas=metadatas[i:i + BATCH_SIZE],
                    ids=ids[i:i + BATCH_SIZE]
                )
            
            # Mark as completed
            async with async_session_factory() as db:
                await db.execute(
                    update(DocumentMetadata)
                    .where(DocumentMetadata.id == doc_meta.id)
                    .values(ingestion_status="completed")
                )
                await db.commit()
                
            logger.info(f"Successfully indexed: {filename} for user {user_id}")
        except Exception as doc_err:
            logger.error(f"Ingestion error for {filename}: {doc_err}")
            async with async_session_factory() as db:
                await db.execute(update(DocumentMetadata).where(DocumentMetadata.id == doc_meta.id).values(ingestion_status="error"))
                await db.commit()

            logger.error(f"Failed to process document {filename}: {doc_err}")

    clear_chat_cache()
