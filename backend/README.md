# RAG Chatbot — Backend

FastAPI backend powering a production-grade RAG pipeline with **ChromaDB** local persistent storage and **Google Gemini** LLM.

## Tech Stack

- **FastAPI** — high-performance, async Python web framework
- **LangChain** — orchestrates the RAG pipeline (splitting, retrieval, LLM calls)
- **ChromaDB** — local persistent vector database (no external service required)
- **PyMuPDF** — reliable PDF text extraction
- **Google Gemini API** — embeddings (`gemini-embedding-2`) + LLM (`gemini-2.0-flash`)

## Setup

### 1. Python Environment
```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate # macOS/Linux
pip install -r requirements.txt
```

### 2. Environment Configuration
Create a `.env` file from the example:
```bash
cp .env.example .env
```
Ensure `GOOGLE_API_KEY` is set. No external database URL is required as ChromaDB runs locally.

### 3. Database Persistence
ChromaDB stores all vectors and metadata locally in:
`backend/app/db/chroma_db/`

This ensures that your indexed documents survive server restarts and are instantly available.

---

## RAG Pipeline Overview

### 1. Ingestion (Background Processing)
- **Parsing**: Scans `backend/app/data/pdfs/` using **PyMuPDF**.
- **Chunking**: Uses `RecursiveCharacterTextSplitter` (`chunk_size=500`, `overlap=50`).
- **Persistence Check**: Before indexing, the system queries the local ChromaDB to check if the document is already indexed to avoid duplicates.
- **Embedding**: Generates vectors using `models/gemini-embedding-2`.
- **Storage**: Chunks are stored with metadata in the local **ChromaDB** persist directory.

### 2. Retrieval & Generation
- **Similarity Search**: User queries are embedded and matched against ChromaDB using Cosine Similarity.
- **Grounding**: The top 4 context chunks are injected into a strict system prompt.
- **LLM Generation**: `gemini-2.0-flash` generates an answer based **strictly** on the provided context.

---

## API Endpoints

- `POST /api/chat`: Grounded question answering.
- `POST /api/upload`: Upload PDFs for background ingestion.
- `GET /api/documents`: List currently indexed documents.
- `GET /`: Health check and system status.
