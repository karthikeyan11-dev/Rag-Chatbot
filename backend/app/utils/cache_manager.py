import os
import json
import hashlib
import logging

logger = logging.getLogger(__name__)

CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "cache")
CACHE_FILE = os.path.join(CACHE_DIR, "chat_cache.json")

def _get_cache_key(question: str, collection_size: int) -> str:
    """Create a unique key based on the question and current DB size."""
    # We include collection_size so that if the DB changes, the cache invalidates
    combined = f"{question}_{collection_size}"
    return hashlib.md5(combined.encode()).hexdigest()

def get_cached_answer(question: str, collection_size: int) -> dict:
    """Retrieve an answer from the local cache if it exists."""
    if not os.path.exists(CACHE_FILE):
        return None
    
    try:
        with open(CACHE_FILE, "r") as f:
            cache = json.load(f)
        
        key = _get_cache_key(question, collection_size)
        if key in cache:
            logger.info(f"Cache hit for question: {question}")
            return cache[key]
    except Exception as e:
        logger.error(f"Error reading chat cache: {e}")
    
    return None

def save_answer_to_cache(question: str, collection_size: int, response: dict):
    """Save a successful answer to the local cache."""
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        
        cache = {}
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, "r") as f:
                cache = json.load(f)
        
        key = _get_cache_key(question, collection_size)
        cache[key] = response
        
        with open(CACHE_FILE, "w") as f:
            json.dump(cache, f, indent=2)
            
        logger.info(f"Saved response to cache for: {question}")
    except Exception as e:
        logger.error(f"Error saving to chat cache: {e}")

def clear_chat_cache():
    """Clear all cached responses (useful when new documents are added)."""
    if os.path.exists(CACHE_FILE):
        try:
            os.remove(CACHE_FILE)
            logger.info("Chat cache cleared.")
        except Exception as e:
            logger.error(f"Error clearing chat cache: {e}")
