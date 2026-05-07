# RAG Chatbot — Company Policy Assistant

A production-quality RAG chatbot that lets employees ask questions about company policy PDFs and receive grounded answers sourced from those documents.

---

## Architecture Overview

```
User Question
     │
     ▼
 React Frontend (Vite)
     │
     ▼ POST /api/chat
 FastAPI Backend
     │
     ├─► ChromaDB (similarity search, top_k=4)
     │        │
     │        └─► Retrieved Chunks + Metadata
     │
     ├─► Prompt Builder (grounded system prompt)
     │
     └─► OpenAI GPT-4o-mini
              │
              ▼
         Answer + Sources
              │
              ▼
     React Frontend displays response
```

### RAG Pipeline

1. **Ingestion** (runs once at backend startup):
   - Scans `backend/app/data/pdfs/` for PDFs
   - Extracts text per-page using PyMuPDF
   - Splits text into 500-token chunks with 50-token overlap using `RecursiveCharacterTextSplitter`
   - Embeds chunks using `text-embedding-3-small`
   - Stores embeddings + metadata in ChromaDB (persisted locally)

2. **Retrieval** (per query):
   - Embeds the user question
   - Performs cosine similarity search in ChromaDB
   - Returns top 4 most relevant chunks

3. **Generation** (per query):
   - Builds a strict grounded prompt with retrieved context
   - Calls `gpt-4o-mini` with `temperature=0` for deterministic answers
   - Returns answer + source document names

---

## Tech Stack

| Layer      | Technology                        |
|------------|-----------------------------------|
| Backend    | Python, FastAPI, Uvicorn          |
| RAG        | LangChain                         |
| Vector DB  | ChromaDB (local persistence)      |
| PDF Parser | PyMuPDF                           |
| LLM        | OpenAI gpt-4o-mini                |
| Embeddings | OpenAI text-embedding-3-small     |
| Frontend   | React 18, Vite                    |
| Styling    | TailwindCSS, Livvic font          |

---

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- OpenAI API key

### 1. Clone and navigate

```bash
git clone <repo-url>
cd rag-chatbot-project
```

### 2. Set up the backend

```bash
cd backend
python -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env — add your OPENAI_API_KEY
```

### 3. Add your PDF documents

```bash
# Place your company policy PDFs here:
backend/app/data/pdfs/
```

### 4. Start the backend

```bash
uvicorn app.main:app --reload --port 8000
```

The backend will automatically ingest all PDFs on startup.

### 5. Set up and start the frontend

```bash
# In a new terminal:
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` in your browser.

---

## Design Decisions

### Why ChromaDB?
- Runs fully locally — no external service or Docker required
- Persistent across restarts (data survives server restarts)
- Native LangChain integration
- Sufficient performance for assessment/production-small scale

### Why chunk_size=500, overlap=50?
- 500 tokens captures a full paragraph of policy text — enough context to answer most questions
- 50-token overlap ensures answers aren't lost when they span chunk boundaries
- Prevents the retriever from returning overly broad or overly narrow chunks

### Why gpt-4o-mini?
- Excellent instruction-following for grounded prompting
- Low latency, cost-effective
- `temperature=0` ensures deterministic, non-hallucinated responses

### Why top_k=4?
- Retrieves enough context for multi-part questions
- Avoids context window bloat from too many chunks
- Covers answers that span multiple document sections

---

## Project Structure

```
rag-chatbot-project/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app + startup ingestion
│   │   ├── routes/chat.py       # POST /api/chat endpoint
│   │   ├── services/
│   │   │   ├── ingest.py        # PDF → chunks → ChromaDB
│   │   │   ├── rag_pipeline.py  # Retrieve → prompt → LLM
│   │   │   ├── vector_store.py  # ChromaDB singleton
│   │   │   └── llm_service.py   # OpenAI LLM singleton
│   │   ├── utils/
│   │   │   └── prompt_template.py  # Grounded system prompt
│   │   ├── data/pdfs/           # Place your PDFs here
│   │   └── db/chroma_db/        # Auto-created vector store
│   ├── requirements.txt
│   ├── .env.example
│   └── README.md
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ChatWindow.jsx   # Message thread + empty state
│   │   │   ├── ChatMessage.jsx  # Individual message bubble
│   │   │   ├── ChatInput.jsx    # Textarea + send button
│   │   │   ├── SourceList.jsx   # Source document badges
│   │   │   └── Loader.jsx       # Animated thinking indicator
│   │   ├── services/api.js      # fetch wrapper for /api/chat
│   │   ├── App.jsx              # Root component + state
│   │   ├── main.jsx             # React entry point
│   │   └── index.css            # Tailwind + global styles
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   └── README.md
└── README.md
```

---

## API Reference

### `POST /api/chat`

**Request:**
```json
{ "question": "What is the maternity leave policy?" }
```

**Response:**
```json
{
  "answer": "The maternity leave policy allows 26 weeks of paid leave...",
  "sources": ["HR Policy 2024.pdf", "Leave Guidelines.pdf"]
}
```

**Error responses:**
- `400` — Empty question or question too long (>2000 chars)
- `500` — LLM or retrieval failure
