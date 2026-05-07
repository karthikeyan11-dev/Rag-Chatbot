# RAG Chatbot — Backend

FastAPI backend powering the RAG pipeline with Qdrant vector storage and Google Gemini LLM.

## Tech Stack

- **FastAPI** — lightweight, async Python web framework
- **LangChain** — orchestrates the RAG pipeline (splitting, retrieval, LLM calls)
- **Qdrant** — high-performance vector database (running in Docker)
- **PyMuPDF** — fast, reliable PDF text extraction
- **Google Gemini API** — embeddings (`models/gemini-embedding-2`) + LLM (`gemini-1.5-flash`)

## Setup

### 1. Create and activate a virtual environment

```bash
cd backend
python -m venv venv
source venv/bin/activate       # macOS/Linux
venv\Scripts\activate          # Windows
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
# Edit .env and add your Gemini API key
GOOGLE_API_KEY=your_gemini_api_key_here
```

### 4. Add company policy PDFs

Place your PDF files inside:

```
backend/app/data/pdfs/
```

The backend ingests all `.pdf` files in this folder automatically on startup.

### 5. Start the server

```bash
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`.

---

## API Endpoints

### `POST /api/chat`

Send a question and receive a grounded answer.

**Request:**
```json
{ "question": "What is the leave policy for sick days?" }
```

**Response:**
```json
{
  "answer": "Employees are entitled to 12 sick days per year...",
  "sources": ["Leave Policy.pdf", "HR Policy.pdf"]
}
```

### `GET /`

Health check — returns `{ "status": "ok" }`.

---

## RAG Pipeline Explanation

### 1. Ingestion (on startup)

1. Scans `backend/app/data/pdfs/` for PDF files
2. Extracts text per page using **PyMuPDF**
3. Chunks text using **RecursiveCharacterTextSplitter**
   - `chunk_size=500` — balances context richness with retrieval precision
   - `chunk_overlap=50` — ensures no information is lost at chunk boundaries
4. Stores chunks + metadata (source filename, page number, chunk index) in **ChromaDB**

### 2. Retrieval

- User question is embedded using `models/embedding-001`
- ChromaDB performs cosine similarity search
- Top 4 (`top_k=4`) most relevant chunks are retrieved

### 3. Generation

- Retrieved chunks are assembled into a context block
- A strict grounded system prompt instructs the LLM:
  - Answer ONLY from provided context
  - Do NOT hallucinate
  - If answer is unavailable: `"I don't have that information in the company documents."`
- `gemini-1.5-flash` generates the final answer

### Why ChromaDB?

- Runs fully locally, no external service needed
- Persistent storage across restarts
- Native LangChain integration
- Fast enough for assessment/demo scale

### Why chunk_size=500, overlap=50?

- `500` tokens captures enough context per chunk for meaningful retrieval without being too broad
- `50` token overlap prevents answers from being split at chunk boundaries
- Empirically well-suited for policy documents with structured paragraphs
