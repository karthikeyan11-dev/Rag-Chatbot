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

def get_hybrid_retriever(user_id: int = None):
    """
    Initialize or return a BM25 retriever focused on specific user's documents.
    Audit: User-scoped to prevent cross-tenant retrieval.
    """
    try:
        store = get_vector_store()
        
        # Scope to current user's documents in ChromaDB metadata
        filters = {}
        if user_id is not None:
            filters = {"user_id": user_id}
            
        results = store._collection.get(where=filters)
        
        if not results["documents"]:
            return None
            
        documents = []
        for i in range(len(results["documents"])):
            documents.append(Document(
                page_content=results["documents"][i],
                metadata=results["metadatas"][i]
            ))
            
        retriever = BM25Retriever.from_documents(documents)
        retriever.k = TOP_K_KEYWORD
        return retriever
    except Exception as e:
        logger.error(f"Audit: BM25 build error for user {user_id}: {e}")
        return None

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    reraise=True
)
def perform_hybrid_search(query: str, user_id: int = None) -> list[Document]:
    """Perform Hybrid Search and deduplicate with user-scoped isolation."""
    # 1. Scoped Vector Search
    vector_docs = similarity_search(query, top_k=TOP_K_VECTOR, user_id=user_id)
    
    # 2. Scoped Keyword Search (BM25)
    keyword_docs = []
    retriever = get_hybrid_retriever(user_id=user_id)
    if retriever:
        keyword_docs = retriever.invoke(query)
    
    seen_ids = set()
    unique_docs = []
    
    for doc in vector_docs + keyword_docs:
        # User isolation double-check
        if user_id is not None and doc.metadata.get("user_id") != user_id:
            logger.warning(f"SECURITY AUDIT: Blocked cross-tenant doc leak for user {user_id}")
            continue
            
        # Hardened deduplication using source + page + chunk_index
        src = doc.metadata.get('source', 'unknown')
        pg = doc.metadata.get('page', '0')
        idx = doc.metadata.get('chunk_index', '0')
        content_id = f"{src}_{pg}_{idx}"
        
        if content_id not in seen_ids:
            unique_docs.append(doc)
            seen_ids.add(content_id)
            
    return unique_docs[:FINAL_K]

async def get_answer(question: str, chat_history: list = None, user_id: int = None) -> dict:
    """Hardened RAG pipeline with strict grounding and user-scoped isolation."""
    # 1. HYBRID RETRIEVAL (Scoped to user)
    try:
        # perform_hybrid_search is a sync function that calls blocking Chroma/BM25 code
        docs = await asyncio.to_thread(perform_hybrid_search, question, user_id=user_id)
    except Exception as e:
        logger.error(f"Audit: Retrieval error for user {user_id}: {e}")
        return {"answer": "I encountered an error accessing your documents.", "sources": []}

    if not docs:
        return {
            "answer": "I could not find information related to that question in your uploaded documents.",
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
        # llm.invoke is a blocking network call
        response = await asyncio.to_thread(llm.invoke, messages)
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
            # Handle potential path vs filename
            clean_filename = raw_source.split('/')[-1].split('\\')[-1] 
            page_num = doc.metadata.get("page", "?")
            
            # Grounding check: ensure the LLM actually discussed this document
            # or include if few docs to be helpful
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
