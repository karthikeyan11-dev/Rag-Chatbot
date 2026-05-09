import os
import logging
from langchain_community.vectorstores import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from dotenv import load_dotenv

load_dotenv()

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Persistence settings
DB_DIR = os.path.join(os.path.dirname(__file__), "..", "db", "chroma_db")
DB_DIR = os.path.abspath(DB_DIR)
COLLECTION_NAME = "company_policies"

_vector_store = None

def get_vector_store() -> Chroma:
    """Return a singleton Chroma vector store instance with local persistence."""
    global _vector_store
    if _vector_store is None:
        try:
            # Ensure the DB directory exists with absolute path
            os.makedirs(DB_DIR, exist_ok=True)
            logger.info(f"Using ChromaDB directory: {DB_DIR}")

            embeddings = GoogleGenerativeAIEmbeddings(
                model="models/embedding-001",
                google_api_key=os.getenv("GOOGLE_API_KEY"),
                task_type="retrieval_document"
            )

            # Initialize Chroma with local persistence
            # Use the newer from_documents/existing_collection logic if needed, 
            # but for a singleton, this constructor is standard for loading.
            _vector_store = Chroma(
                collection_name=COLLECTION_NAME,
                embedding_function=embeddings,
                persist_directory=DB_DIR
            )
            
            # Verify connection by counting items
            count = _vector_store._collection.count()
            logger.info(f"ChromaDB initialized successfully. Collection size: {count}")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            # Do not raise here, let it return None and handle downstream
            _vector_store = None
            
    return _vector_store

def reset_vector_store():
    """Reset the singleton instance."""
    global _vector_store
    _vector_store = None

def similarity_search(query: str, top_k: int = 6):
    """Perform similarity search and return top_k documents with score filtering."""
    store = get_vector_store()
    if store is None:
        logger.error("Vector store is not initialized. Cannot perform search.")
        return []
    
    # Use similarity_search_with_score to get distance scores
    docs_and_scores = store.similarity_search_with_score(query, k=top_k)
    
    # Filter out chunks with poor similarity 
    # Relaxed to 0.9 for universal reliability across different document types
    # We rely on the LLM's re-ranking step in the pipeline to pick the best ones.
    THRESHOLD = 0.9
    filtered_docs = [doc for doc, score in docs_and_scores if score < THRESHOLD]
    
    logger.info(f"Search returned {len(docs_and_scores)} total; {len(filtered_docs)} passed threshold {THRESHOLD}")
    return filtered_docs

def get_collection_size() -> int:
    """Return the number of documents in the collection safely."""
    try:
        # For Chroma, we can access the underlying collection
        store = get_vector_store()
        if store is None:
            return 0
        # count() returns the number of items in the collection
        return store._collection.count()
    except Exception as e:
        logger.error(f"Error checking ChromaDB collection status: {e}")
        return 0

def delete_document_vectors(filename: str) -> bool:
    """
    Delete all vectors and chunks related to a specific document from ChromaDB.
    Uses metadata filtering on the 'source' field.
    """
    try:
        store = get_vector_store()
        if store is None:
            logger.error("Vector store not initialized. Cannot delete vectors.")
            return False
        
        # ChromaDB raw collection deletion with metadata filter
        # In our ingestion, 'source' contains the filename
        store._collection.delete(where={"source": filename})
        logger.info(f"Successfully deleted all vectors for document: {filename}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete vectors for {filename}: {e}")
        return False
