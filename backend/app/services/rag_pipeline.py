import logging
from langchain.schema import HumanMessage, SystemMessage
from app.services.vector_store import similarity_search, get_collection_size
from app.services.llm_service import get_llm
from app.utils.prompt_template import build_system_prompt

# Configure logging
logger = logging.getLogger(__name__)

from tenacity import retry, stop_after_attempt, wait_exponential

from app.utils.cache_manager import get_cached_answer, save_answer_to_cache

TOP_K = 15

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    reraise=True
)
def _safe_similarity_search(question: str):
    return similarity_search(question, top_k=TOP_K)

def get_answer(question: str) -> dict:
    """
    Production-Grade RAG pipeline with Response Caching:
    1. Check local cache for identical question/state.
    2. Retrieve Top 15 chunks (increased depth).
    3. SMART RE-RANKING: The LLM will identify the most relevant context from the broad set.
    4. Grounded generation + Cache save.
    """
    # Verify if any documents exist in the vector store
    collection_size = get_collection_size()
    logger.info(f"ChromaDB collection size: {collection_size} chunks")
    
    if collection_size == 0:
        return {
            "answer": "The Knowledge Base is currently being updated or is empty. Please wait a moment or upload documents.",
            "sources": [],
        }

    # 1. CHECK CACHE FIRST
    cached_res = get_cached_answer(question, collection_size)
    if cached_res:
        return cached_res

    # 2. PROCEED TO RAG IF NOT CACHED
    try:
        docs = _safe_similarity_search(question)
        logger.info(f"High-recall search returned {len(docs)} documents.")
    except Exception as e:
        logger.error(f"Error during search: {e}")
        return {"answer": "I encountered an error accessing the document database.", "sources": []}

    if not docs:
        return {"answer": "I could not find any relevant information.", "sources": []}

    # Assemble context
    context_parts = []
    for doc in docs:
        source = doc.metadata.get("source", "Unknown")
        page = doc.metadata.get("page", "?")
        # We use the raw page_content which now includes the enrichment prefix
        context_parts.append(doc.page_content)

    context = "\n\n---\n\n".join(context_parts)

    # Generate grounded response
    system_prompt = build_system_prompt(context)
    llm = get_llm()

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=question),
    ]

    try:
        response = llm.invoke(messages)
        answer = response.content.strip()

        # Fallback check
        fallback_phrases = ["i don't have that information", "cannot find", "not mentioned"]
        if any(phrase in answer.lower() for phrase in fallback_phrases):
            return {"answer": "I could not find that information in the documents.", "sources": []}

        # DYNAMIC SOURCE ATTRIBUTION:
        # Group pages by document for a cleaner UI
        doc_pages = {} # {filename: set(pages)}
        for doc in docs:
            src_name = doc.metadata.get("source")
            page_num = doc.metadata.get("page")
            
            # Only include if the document name is mentioned in the answer
            if src_name in answer:
                if src_name not in doc_pages:
                    doc_pages[src_name] = set()
                doc_pages[src_name].add(str(page_num))

        # Format grouped sources as strings
        logger.info(f"Grouping sources for {len(doc_pages)} unique documents.")
        source_strings = []
        for src_name, pages in doc_pages.items():
            sorted_pages = sorted(list(pages), key=lambda x: int(x) if x.isdigit() else 999)
            pages_str = ", ".join(sorted_pages)
            source_strings.append(f"{src_name} (Pages: [{pages_str}])")

        # Fallback if no sources found
        if not source_strings and docs:
            top_src = docs[0].metadata['source']
            top_page = docs[0].metadata['page']
            source_strings = [f"{top_src} (Page {top_page})"]

        # Clean answer
        import re
        clean_answer = re.sub(r'\[Source:.*?\]', '', answer, flags=re.IGNORECASE)
        clean_answer = re.sub(r'\(Source:.*?\)', '', clean_answer, flags=re.IGNORECASE)
        clean_answer = re.sub(r'Source:.*$', '', clean_answer, flags=re.IGNORECASE | re.MULTILINE)
        clean_answer = clean_answer.strip()

        result = {
            "answer": clean_answer,
            "sources": source_strings,
        }
        
        # 3. SAVE TO CACHE
        save_answer_to_cache(question, collection_size, result)

        return result
    except Exception as e:
        logger.error(f"LLM Error during generation: {e}")
        
        # Check for specific Gemini/Google API errors
        err_msg = str(e).lower()
        if "429" in err_msg or "quota" in err_msg or "rate limit" in err_msg:
            return {
                "answer": "Gemini API request failed due to rate limiting. Please try again in 30-60 seconds.",
                "sources": [],
            }
        
        if "api key" in err_msg or "authentication" in err_msg or "permission" in err_msg:
            return {
                "answer": "There is an issue with the AI service configuration. Please contact the system administrator.",
                "sources": [],
            }
        
        return {
            "answer": "I encountered an error while generating an answer. This might be due to a temporary connection issue with the AI service. Please try again in a moment.",
            "sources": [],
        }

