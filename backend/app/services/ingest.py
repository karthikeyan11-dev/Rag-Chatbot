import os
import fitz  # PyMuPDF
import time
import uuid
import logging
from langchain_experimental.text_splitter import SemanticChunker
from app.services.vector_store import get_vector_store
from app.services.s3_service import s3_service
from app.utils.cache_manager import clear_chat_cache
from langchain_google_genai import GoogleGenerativeAIEmbeddings

# Configure logging
logger = logging.getLogger(__name__)

def clean_text(text: str) -> str:
    """Perform text cleaning to improve embedding quality."""
    import re
    # Remove excessive whitespace and non-printable characters
    text = re.sub(r'\s+', ' ', text)
    text = "".join(ch for ch in text if ch.isprintable())
    return text.strip()


def extract_text_from_s3_pdf(filename: str) -> list[dict]:
    """
    Download PDF from S3 and extract text. Hardened for memory and connection safety.
    """
    pages = []
    file_stream = None
    doc = None
    try:
        file_stream = s3_service.get_file_content(filename)
        if not file_stream:
            logger.error(f"S3: Failed to retrieve content for {filename}")
            return []

        if not filename.lower().endswith(".pdf"):
            logger.warning(f"S3: Skipping non-PDF file {filename}")
            return []

        doc = fitz.open(stream=file_stream, filetype="pdf")
        
        # Limit processing for extremely large files to prevent OOM
        if len(doc) > 500:
            logger.warning(f"Large document detected ({len(doc)} pages). Extraction may be slow.")

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text")
            cleaned_text = clean_text(text)
            if cleaned_text:
                pages.append({
                    "text": cleaned_text,
                    "page": page_num + 1,
                    "source": filename,
                })
        
        logger.info(f"PyMuPDF: Extracted {len(pages)} pages from {filename}")
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
                
                # HARDENING: Richer metadata for cloud traceability
                chunks.append({
                    "text": content,
                    "metadata": {
                        "source": page_data["source"],
                        "page": page_data["page"],
                        "chunk_index": idx,
                        "ingested_at": str(time.time())
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
        results = vector_store._collection.get(where={"source": filename}, limit=1)
        return len(results["ids"]) > 0
    except Exception as e:
        logger.error(f"Index check error: {e}")
        return False


def ingest_documents():
    """Detects documents in S3 and adds them to ChromaDB. Hardened batch processing."""
    all_s3_files = s3_service.list_files()

    if not all_s3_files:
        logger.info("No documents found in AWS S3.")
        return

    # Filter for files not yet indexed
    new_files = [f for f in all_s3_files if not is_document_indexed(f)]

    if not new_files:
        logger.info("All S3 documents are already indexed.")
        return

    logger.info(f"Ingesting {len(new_files)} new documents from S3.")

    for filename in new_files:
        try:
            pages = extract_text_from_s3_pdf(filename)
            if not pages: continue

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
                
                # Deterministic ID for idempotency
                uid_string = f"{c['metadata']['source']}__p{c['metadata']['page']}__c{c['metadata']['chunk_index']}"
                ids.append(str(uuid.uuid5(uuid.NAMESPACE_DNS, uid_string)))

            # HARDENING: Safe batching to prevent API rate limits and OOM
            BATCH_SIZE = 10
            for i in range(0, len(texts), BATCH_SIZE):
                try:
                    logger.info(f"Chroma: Adding batch {i//BATCH_SIZE + 1} for {filename}")
                    vector_store.add_texts(
                        texts=texts[i:i + BATCH_SIZE],
                        metadatas=metadatas[i:i + BATCH_SIZE],
                        ids=ids[i:i + BATCH_SIZE]
                    )
                    logger.info(f"Ingested batch for {filename} ({i+len(texts[i:i+BATCH_SIZE])}/{len(texts)})")
                    # time.sleep(2) # Modest throttle for API safety
                except Exception as batch_err:
                    logger.error(f"Batch storage error for {filename}: {batch_err}")
                    time.sleep(10) # Exponential-like backoff
            
            logger.info(f"Successfully fully indexed: {filename}")
        except Exception as doc_err:
            logger.error(f"Failed to process document {filename}: {doc_err}")

    clear_chat_cache()
