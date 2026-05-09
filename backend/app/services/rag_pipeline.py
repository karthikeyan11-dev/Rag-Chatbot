import logging
import re
import asyncio
from langchain.schema import HumanMessage, SystemMessage, AIMessage, Document
from langchain_community.retrievers import BM25Retriever
from app.services.vector_store import similarity_search, get_collection_size, get_vector_store
from app.services.llm_service import get_llm
from app.utils.prompt_template import build_system_prompt
from app.utils.cache_manager import get_cached_answer, save_answer_to_cache
from tenacity import retry, stop_after_attempt, wait_exponential
from sqlalchemy import select, func
from app.db.database import async_session_factory
from app.db.models import DocumentMetadata

# Configure logging
logger = logging.getLogger(__name__)

# Constants for retrieval
TOP_K_VECTOR = 10
TOP_K_KEYWORD = 10
FINAL_K = 15

# Global cache for BM25 retriever
_bm25_retriever = None
_last_cache_key = None

async def _get_collection_hash():
    """Generate a cache key based on collection size and latest modification date in RDS."""
    try:
        size = get_collection_size()
        if size == 0:
            return "empty"
        
        # Get latest document update timestamp from RDS
        async with async_session_factory() as db:
            result = await db.execute(select(func.max(DocumentMetadata.upload_date)))
            max_date = result.scalar()
            max_date_str = max_date.isoformat() if max_date else "none"
            
        return f"{size}_{max_date_str}"
    except Exception as e:
        logger.warning(f"Audit: Failed to generate collection hash: {e}")
        return str(get_collection_size())

def get_hybrid_retriever():
    """
    Initialize or return a cached BM25 retriever.
    Audit: Improved cache invalidation using RDS metadata timestamps.
    """
    global _bm25_retriever, _last_cache_key
    
    # Run async hash generation in the current loop (or a new one if needed)
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # In a request context, we use a specialized helper to avoid blocking
            # For simplicity in this audit, we'll use a synchronous-friendly approach or block briefly
            cache_key = asyncio.run_coroutine_threadsafe(_get_collection_hash(), loop).result()
        else:
            cache_key = asyncio.run(_get_collection_hash())
    except Exception:
        # Fallback to just size if async retrieval fails
        cache_key = str(get_collection_size())

    if _bm25_retriever is not None and cache_key == _last_cache_key:
        return _bm25_retriever
    
    if cache_key.startswith("0") or cache_key == "empty":
        return None
        
    try:
        logger.info(f"Audit: Rebuilding BM25 index (Reason: Cache invalid or stale). Key: {cache_key}")
        store = get_vector_store()
        results = store._collection.get()
        
        documents = []
        for i in range(len(results["documents"])):
            documents.append(Document(
                page_content=results["documents"][i],
                metadata=results["metadatas"][i]
            ))
            
        _bm25_retriever = BM25Retriever.from_documents(documents)
        _bm25_retriever.k = TOP_K_KEYWORD
        _last_cache_key = cache_key
        return _bm25_retriever
    except Exception as e:
        logger.error(f"Audit: BM25 build error: {e}")
        return None

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    reraise=True
)
def perform_hybrid_search(query: str) -> list[Document]:
    """Perform Hybrid Search and deduplicate with hardened ID logic."""
    vector_docs = similarity_search(query, top_k=TOP_K_VECTOR)
    
    keyword_docs = []
    retriever = get_hybrid_retriever()
    if retriever:
        keyword_docs = retriever.invoke(query)
    
    seen_ids = set()
    unique_docs = []
    
    for doc in vector_docs + keyword_docs:
        # Hardened deduplication using source + page + chunk_index
        src = doc.metadata.get('source', 'unknown')
        pg = doc.metadata.get('page', '0')
        idx = doc.metadata.get('chunk_index', '0')
        content_id = f"{src}_{pg}_{idx}"
        
        if content_id not in seen_ids:
            unique_docs.append(doc)
            seen_ids.add(content_id)
            
    return unique_docs[:FINAL_K]

def get_answer(question: str, chat_history: list = None) -> dict:
    """Hardened RAG pipeline with strict grounding and verified source attribution."""
    collection_size = get_collection_size()
    
    if collection_size == 0:
        return {
            "answer": "No company documents were uploaded. Please upload PDFs to the Knowledge Base to begin.",
            "sources": [],
        }

    # 1. HYBRID RETRIEVAL
    try:
        docs = perform_hybrid_search(question)
    except Exception as e:
        logger.error(f"Audit: Retrieval error: {e}")
        return {"answer": "I encountered an error accessing the knowledge base.", "sources": []}

    if not docs:
        return {
            "answer": "I could not find information related to that question in the uploaded company documents.",
            "sources": []
        }

    # 2. GENERATION
    system_prompt = build_system_prompt("\n\n---\n\n".join([doc.page_content for doc in docs]))
    llm = get_llm()

    messages = [SystemMessage(content=system_prompt)]
    if chat_history:
        for turn in chat_history[-10:]:
            role_msg = HumanMessage(content=turn["content"]) if turn["role"] == "user" else AIMessage(content=turn["content"])
            messages.append(role_msg)
    
    messages.append(HumanMessage(content=question))

    try:
        response = llm.invoke(messages)
        answer = response.content.strip()

        # Strict Fallback Check
        fallback_phrase = "I could not find information related to that question"
        if fallback_phrase.lower() in answer.lower() or "don't have that information" in answer.lower():
            return {
                "answer": "I could not find information related to that question in the uploaded company documents.",
                "sources": []
            }

        # 3. VERIFIED SOURCE ATTRIBUTION
        doc_pages = {}
        for doc in docs:
            raw_source = doc.metadata.get("source", "Unknown")
            clean_filename = raw_source.split('/')[-1]
            page_num = doc.metadata.get("page", "?")
            
            # Grounding check: ensure the LLM actually discussed this document
            if clean_filename.lower() in answer.lower() or len(docs) <= 3:
                if clean_filename not in doc_pages:
                    doc_pages[clean_filename] = set()
                doc_pages[clean_filename].add(str(page_num))

        source_strings = []
        for src, pages in doc_pages.items():
            sorted_pages = sorted(list(pages), key=lambda x: int(x) if x.isdigit() else 999)
            source_strings.append(f"{src} (Page: {', '.join(sorted_pages)})")

        return {
            "answer": re.sub(r'[\[\(]Source:.*?[\]\)]', '', answer, flags=re.IGNORECASE).strip(),
            "sources": source_strings,
        }
    except Exception as e:
        logger.error(f"Audit: LLM Error: {e}")
        return {"answer": "The AI service is temporarily unavailable.", "sources": []}
