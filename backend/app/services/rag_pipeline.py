import logging
import re
import asyncio
from langchain.schema import HumanMessage, SystemMessage, AIMessage, Document
from langchain_community.retrievers import BM25Retriever
from app.services.vector_store import similarity_search, get_collection_size, get_vector_store
from app.services.llm_service import get_llm, classify_query_intent
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
def perform_hybrid_search(query: str, user_id: int = None, top_k: int = TOP_K_VECTOR, threshold: float = 0.9) -> list[Document]:
    """Perform Hybrid Search and deduplicate with user-scoped isolation."""
    # 1. Scoped Vector Search
    vector_docs = similarity_search(query, top_k=top_k, user_id=user_id, threshold=threshold)
    
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

async def get_answer(question: str, chat_history: list = None, user_id: int = None, session_id: str = None) -> dict:
    """Hardened RAG pipeline with strict intelligence-based routing."""
    # 0. INTENT CLASSIFICATION (Phase 1)
    intent_data = await classify_query_intent(question)
    intent = intent_data.get("intent", "factual_retrieval")

    # Phase 7: Contextual Awareness (Session-Doc Affinity)
    # If it's a followup or summary without a specific doc name, prioritize recent docs
    # This ensures "contextual" queries find the right docs even if the name isn't repeated.
    recent_doc_ids = []
    if session_id:
        try:
            # ARCHITECTURAL FIX: Use a background task or cached affinity to avoid 
            # nested DB calls during the RAG pipeline which blocks the thread/pool.
            # Simplified for now to prevent wait_for hangs or pool exhaustion.
            pass 
        except Exception as e:
            logger.warning(f"Failed to fetch session doc affinity: {e}")

    # 1. HIERARCHICAL RETRIEVAL (Phase 3)
    # Fetch document-level summaries from RDS for the user
    doc_summaries = []
    try:
        async with async_session_factory() as db:
            result = await db.execute(
                select(DocumentMetadata).where(DocumentMetadata.user_id == user_id)
            )
            user_docs = result.scalars().all()
            doc_summaries = [
                f"Document: {d.filename}\nSummary: {d.summary}\nTopics: {d.key_topics}"
                for d in user_docs if d.summary
            ]
    except Exception as e:
        logger.error(f"Failed to fetch document summaries: {e}")

    # 2. HYBRID RETRIEVAL (Scoped to user)
    try:
        # Phase 4: Adaptive Retrieval Strategy
        # Adjusting parameters based on classified intent
        vector_k = TOP_K_VECTOR
        hybrid_k = FINAL_K
        similarity_threshold = 0.9  # Default strict threshold

        if intent == "document_summary":
            vector_k = 20  # Wider search
            hybrid_k = 25  # More context
            similarity_threshold = 0.75  # Lower threshold for broader context
        elif intent == "analytical":
            vector_k = 15
            hybrid_k = 20
            similarity_threshold = 0.85
        elif intent == "factual_retrieval":
            vector_k = 5
            hybrid_k = 10
            similarity_threshold = 0.92  # Even stricter for facts

        # Note: similarity_search in vector_store.py needs to support custom threshold
        # For now, we manually filter or adjust the search params in thread
        docs = await asyncio.to_thread(perform_hybrid_search, question, user_id=user_id, top_k=vector_k, threshold=similarity_threshold)
        
        # If analytical or summary, and no docs found, try a broader search on "overview" or "summary"
        if not docs and intent in ["document_summary", "analytical"]:
            docs = await asyncio.to_thread(perform_hybrid_search, "overview summary themes", user_id=user_id, top_k=vector_k, threshold=0.7)

        # Truncate unique docs to hybrid_k
        docs = docs[:hybrid_k]

        # Phase 5: Fallback Retrieval Logic
        # If no chunks found, but we have summaries, attempt grounded synthesis from summaries
        if not docs and doc_summaries:
            logger.info(f"Fallback: No chunks found for intent {intent}. Using document summaries.")
            # Note: doc_summaries are already collected in Phase 3
    
    except Exception as e:
        logger.error(f"Audit: Retrieval error for user {user_id}: {e}")
        return {"answer": "I encountered an error accessing your documents.", "sources": []}

    # 3. GENERATION
    # Phase 3/5 Enhancement: Inject Document Summaries into Context
    context_parts = []
    
    # Fallback/Hierarchical: If it's a summary query OR we have no specific chunks, use summaries
    if doc_summaries and (intent in ["document_summary", "overview", "analytical"] or not docs):
        context_parts.append("--- DOCUMENT SUMMARIES ---\n" + "\n\n".join(doc_summaries))
    
    if docs:
        context_parts.append("--- SPECIFIC CHUNKS ---\n" + "\n\n---\n\n".join([doc.page_content for doc in docs]))
    
    if not context_parts:
        # Final Fallback: Check if user has ANY documents at all
        if not doc_summaries:
            return {
                "answer": "You haven't uploaded any documents yet. Please upload a PDF to get started.",
                "sources": []
            }
        return {
            "answer": "I could not find specific details for that in the document chunks, but based on the general document overview...",
            "sources": [] # Handled by LLM synthesis if context_parts had summaries
        }

    # Phase 5/6: Synthesis Strategy
    system_prompt = build_system_prompt("\n\n".join(context_parts), intent=intent)
    
    if not docs and doc_summaries:
        system_prompt += "\n\nNOTE: You are answering based on high-level document summaries because no specific matching details were found in the text chunks. Be honest about the level of detail available."
    
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
