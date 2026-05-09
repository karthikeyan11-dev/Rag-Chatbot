import os
import fitz  # PyMuPDF
import time
import uuid
import logging
from langchain.text_splitter import RecursiveCharacterTextSplitter
from app.services.vector_store import get_vector_store, COLLECTION_NAME
from app.utils.cache_manager import clear_chat_cache

# Configure logging
logger = logging.getLogger(__name__)

PDF_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "pdfs")
PDF_DIR = os.path.abspath(PDF_DIR)

CHUNK_SIZE = 600
CHUNK_OVERLAP = 150


def extract_text_from_pdf(pdf_path: str) -> list[dict]:
    """Extract text from each page of a PDF, returning list of {text, page, source}."""
    pages = []
    try:
        doc = fitz.open(pdf_path)
        filename = os.path.basename(pdf_path)
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            if text.strip():
                pages.append({
                    "text": text,
                    "page": page_num + 1,
                    "source": filename,
                })
        doc.close()
    except Exception as e:
        logger.error(f"Failed to extract text from {pdf_path}: {e}")
    return pages


def chunk_pages(pages: list[dict]) -> list[dict]:
    """Chunk extracted pages using RecursiveCharacterTextSplitter."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = []
    for page_data in pages:
        text_chunks = splitter.split_text(page_data["text"])
        for idx, chunk in enumerate(text_chunks):
            chunks.append({
                "text": chunk.strip(),
                "metadata": {
                    "source": page_data["source"],
                    "page": page_data["page"],
                    "chunk_index": idx,
                },
            })
    return chunks


def is_document_indexed(filename: str) -> bool:
    """Check if a document is already indexed in ChromaDB."""
    try:
        vector_store = get_vector_store()
        # Use raw ChromaDB collection for reliable metadata filtering
        results = vector_store._collection.get(where={"source": filename}, limit=1)
        return len(results["ids"]) > 0
    except Exception as e:
        logger.error(f"Error checking index status for {filename}: {e}")
        return False


def ingest_documents():
    """Main ingestion pipeline: detects new PDFs and adds them to the persistent ChromaDB."""
    if not os.path.exists(PDF_DIR):
        os.makedirs(PDF_DIR, exist_ok=True)
        logger.info(f"Created PDF directory: {PDF_DIR}")

    all_pdf_files = [f for f in os.listdir(PDF_DIR) if f.lower().endswith(".pdf")]

    if not all_pdf_files:
        logger.info(f"No PDFs found in {PDF_DIR}.")
        return

    # Identify new files
    new_pdf_files = []
    for pdf_file in all_pdf_files:
        if is_document_indexed(pdf_file):
            logger.info(f"Document already indexed, skipping: {pdf_file}")
        else:
            new_pdf_files.append(pdf_file)

    if not new_pdf_files:
        logger.info("All documents are already indexed in ChromaDB.")
        return

    logger.info(f"Found {len(new_pdf_files)} new document(s) to ingest: {new_pdf_files}")

    all_pages = []
    for pdf_file in new_pdf_files:
        pdf_path = os.path.join(PDF_DIR, pdf_file)
        logger.info(f"Extracting: {pdf_file}")
        pages = extract_text_from_pdf(pdf_path)
        all_pages.extend(pages)

    if not all_pages:
        logger.info("No text could be extracted from the new documents.")
        return

    chunks = chunk_pages(all_pages)
    
    # ENHANCEMENT: Enrich each chunk with its context for production-grade retrieval
    # By adding the document name and page number to the text, we ensure the vector 
    # model can "see" the relationship between the question and the specific document.
    enriched_chunks = []
    for c in chunks:
        enriched_text = f"Document: {c['metadata']['source']}\nPage: {c['metadata']['page']}\nContent: {c['text']}"
        enriched_chunks.append({
            "text": enriched_text,
            "metadata": c["metadata"]
        })
    
    logger.info(f"Generated {len(enriched_chunks)} context-enriched chunk(s). Storing in ChromaDB...")

    vector_store = get_vector_store()
    if vector_store is None:
        logger.error("Could not initialize vector store. Ingestion aborted.")
        return

    texts = [c["text"] for c in enriched_chunks]
    metadatas = [c["metadata"] for c in enriched_chunks]
    all_ids = []
    for m in metadatas:
        uid_string = f"{m['source']}__p{m['page']}__c{m['chunk_index']}"
        all_ids.append(str(uuid.uuid5(uuid.NAMESPACE_DNS, uid_string)))

    # ChromaDB handles large uploads well, but we must respect LLM rate limits.
    # For Gemini Free Tier, we use a balanced batch size and longer sleep to stay under 15 RPM.
    BATCH_SIZE = 5 
    total_chunks = len(chunks)
    
    logger.info(f"Starting ingestion of {total_chunks} chunks with RPM-safe batching (Size: {BATCH_SIZE})...")

    for i in range(0, total_chunks, BATCH_SIZE):
        batch_texts = texts[i:i + BATCH_SIZE]
        batch_metadatas = metadatas[i:i + BATCH_SIZE]
        batch_ids = all_ids[i:i + BATCH_SIZE]
        
        try:
            vector_store.add_texts(texts=batch_texts, metadatas=batch_metadatas, ids=batch_ids)
            logger.info(f"Stored batch {i//BATCH_SIZE + 1}/{(total_chunks-1)//BATCH_SIZE + 1} ({min(i+BATCH_SIZE, total_chunks)}/{total_chunks} chunks)")
        except Exception as e:
            logger.error(f"Failed to store batch starting at index {i}: {e}")
            if "429" in str(e) or "quota" in str(e).lower():
                logger.info("Rate limit hit. Sleeping for 60 seconds before retry...")
                time.sleep(60)
                try:
                    vector_store.add_texts(texts=batch_texts, metadatas=batch_metadatas, ids=batch_ids)
                    logger.info("Retry successful.")
                except:
                    logger.error("Retry failed. Skipping.")
        
        # 15s sleep between batches of 5 means ~4 batches per minute = 4 API calls/min.
        # This is well below the 15 RPM limit, leaving room for user chat queries.
        if i + BATCH_SIZE < total_chunks:
            time.sleep(15) 

    logger.info(f"Ingestion process complete. Final check of collection size: {get_vector_store()._collection.count()}")
    clear_chat_cache()
