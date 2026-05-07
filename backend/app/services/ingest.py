import os
import fitz  # PyMuPDF
from langchain.text_splitter import RecursiveCharacterTextSplitter
from app.services.vector_store import get_vector_store

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
    """Main ingestion pipeline: load PDFs → extract → chunk → embed → store."""
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
    print(f"Generated {len(chunks)} chunk(s). Storing in ChromaDB...")

    vector_store = get_vector_store()

    # Clear existing collection to avoid stale data or duplicates if files changed
    # In a real production system, you'd use more sophisticated sync logic
    try:
        # Get count before clearing
        count = vector_store._collection.count()
        if count > 0:
            # Re-creating the store is sometimes safer in Chroma if clearing fails
            vector_store.delete_collection()
            # Re-initialize
            vector_store = get_vector_store()
    except Exception as e:
        print(f"Note: Could not clear collection: {e}")

    texts = [c["text"] for c in chunks]
    metadatas = [c["metadata"] for c in chunks]

    # Use unique IDs based on source + page + chunk_index
    ids = [
        f"{m['source']}__p{m['page']}__c{m['chunk_index']}"
        for m in metadatas
    ]

    vector_store.add_texts(texts=texts, metadatas=metadatas, ids=ids)
    print(f"Ingestion complete. {len(chunks)} chunks stored.")
