import os
import fitz  # PyMuPDF
from langchain.text_splitter import RecursiveCharacterTextSplitter
from app.services.vector_store import get_vector_store, reset_vector_store, get_qdrant_client, COLLECTION_NAME

PDF_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "pdfs")
PDF_DIR = os.path.abspath(PDF_DIR)

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50


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
        print(f"Failed to extract text from {pdf_path}: {e}")
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


def ingest_documents():
    """Main ingestion pipeline: load PDFs → extract → chunk → embed → store in Qdrant."""
    if not os.path.exists(PDF_DIR):
        os.makedirs(PDF_DIR, exist_ok=True)
        print(f"Created PDF directory: {PDF_DIR}")

    pdf_files = [f for f in os.listdir(PDF_DIR) if f.lower().endswith(".pdf")]

    if not pdf_files:
        print(f"No PDFs found in {PDF_DIR}.")
        return

    print(f"Found {len(pdf_files)} PDF(s): {pdf_files}")

    all_pages = []
    for pdf_file in pdf_files:
        pdf_path = os.path.join(PDF_DIR, pdf_file)
        print(f"Extracting: {pdf_file}")
        pages = extract_text_from_pdf(pdf_path)
        all_pages.extend(pages)

    if not all_pages:
        print("No text could be extracted from the PDFs.")
        return

    print(f"Extracted {len(all_pages)} page(s). Chunking...")
    chunks = chunk_pages(all_pages)
    print(f"Generated {len(chunks)} chunk(s). Storing in Qdrant...")

    client = get_qdrant_client()

    # Clear existing collection to avoid stale data or duplicates
    try:
        # Some versions of qdrant-client might throw 404 instead of returning False
        exists = False
        try:
            exists = client.collection_exists(COLLECTION_NAME)
        except Exception:
            exists = False

        if exists:
            print(f"Clearing existing collection: {COLLECTION_NAME}")
            client.delete_collection(COLLECTION_NAME)
            # Reset singleton to ensure fresh initialization
            reset_vector_store()
    except Exception as e:
        print(f"Note: Could not clear collection: {e}")

    vector_store = get_vector_store()

    texts = [c["text"] for c in chunks]
    metadatas = [c["metadata"] for c in chunks]

    # Use deterministic UUIDs based on source + page + chunk_index
    # Qdrant requires IDs to be integers or UUIDs
    import uuid
    import time
    
    all_ids = []
    for m in metadatas:
        uid_string = f"{m['source']}__p{m['page']}__c{m['chunk_index']}"
        all_ids.append(str(uuid.uuid5(uuid.NAMESPACE_DNS, uid_string)))

    # Process in batches to avoid Gemini API rate limits (100 RPM for free tier)
    # 5 chunks every 12 seconds = 25 chunks per minute (well under the 100 RPM limit)
    BATCH_SIZE = 5
    total_chunks = len(chunks)
    print(f"Starting ingestion of {total_chunks} chunks in batches of {BATCH_SIZE}...")
    
    for i in range(0, total_chunks, BATCH_SIZE):
        batch_texts = texts[i:i + BATCH_SIZE]
        batch_metadatas = metadatas[i:i + BATCH_SIZE]
        batch_ids = all_ids[i:i + BATCH_SIZE]
        
        print(f"Storing batch {i//BATCH_SIZE + 1}/{(total_chunks-1)//BATCH_SIZE + 1} ({len(batch_texts)} chunks)...")
        vector_store.add_texts(texts=batch_texts, metadatas=batch_metadatas, ids=batch_ids)
        
        if i + BATCH_SIZE < total_chunks:
            print(f"Waiting 12 seconds to avoid rate limits... ({total_chunks - (i + BATCH_SIZE)} chunks remaining)")
            time.sleep(12) 

    print(f"Ingestion complete. {total_chunks} chunks stored in Qdrant.")
