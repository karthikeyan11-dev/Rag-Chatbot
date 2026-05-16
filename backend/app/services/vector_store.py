import os
import logging
import chromadb
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from dotenv import load_dotenv

load_dotenv()

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Cloud settings
CHROMA_API_KEY = os.getenv('CHROMA_API_KEY')
CHROMA_TENANT = os.getenv('CHROMA_TENANT', 'default_tenant')
CHROMA_DATABASE = os.getenv('CHROMA_DATABASE', 'default_database')
CHROMA_HOST = os.getenv('CHROMA_HOST', 'https://api.trychroma.com')
COLLECTION_NAME = os.getenv('CHROMA_COLLECTION_NAME', 'rag-chatbot-documents')

# Persistence settings (for rollback/reference)
DB_DIR = os.path.join(os.path.dirname(__file__), '..', 'chroma_db')
DB_DIR = os.path.abspath(DB_DIR)

_vector_store = None

def get_vector_store() -> Chroma:
     global _vector_store
     if _vector_store is None:
        try:
            logger.info(f'Initializing Chroma Cloud client. Host: {CHROMA_HOST}, Tenant: {CHROMA_TENANT}, DB: {CHROMA_DATABASE}')
            
            if not CHROMA_API_KEY:
                logger.warning('CHROMA_API_KEY not found in environment variables.')

            embeddings = GoogleGenerativeAIEmbeddings(
                model='models/gemini-embedding-2',
                google_api_key=os.getenv('GOOGLE_API_KEY'),
                task_type='retrieval_document'
            )

            # Initialize Remote Client
            remote_client = chromadb.HttpClient(
                host=CHROMA_HOST,
                tenant=CHROMA_TENANT,
                database=CHROMA_DATABASE,
                settings=chromadb.Settings(
                    chroma_client_auth_provider="chromadb.auth.token_authn.TokenAuthClientProvider",
                    chroma_client_auth_credentials=CHROMA_API_KEY,
                    chroma_auth_token_transport_header="X-Chroma-Token"
                )
            )

            _vector_store = Chroma(
                client=remote_client,
                collection_name=COLLECTION_NAME,
                embedding_function=embeddings
            )
            
            count = _vector_store._collection.count()
            logger.info(f'Chroma Cloud initialized successfully. Collection size: {count}')
        except Exception as e:
            logger.error(f'Chroma Cloud Initialization Error: {e}')
            _vector_store = None
     return _vector_store

def similarity_search(query: str, top_k: int = 6, user_id: int = None, threshold: float = 0.9):
    store = get_vector_store()
    if store is None:
        logger.error('Vector store is not initialized. Cannot perform search.')
        return []
    
    # Filter by user_id if provided
    filter_dict = {}
    if user_id is not None:
        filter_dict = {"user_id": user_id}

    docs_and_scores = store.similarity_search_with_score(query, k=top_k, filter=filter_dict)
    
    # Phase 4 support: Adaptive Thresholding
    filtered_docs = [doc for doc, score in docs_and_scores if score < threshold]
    
    logger.info(f'Search returned {len(docs_and_scores)} total for user {user_id}; {len(filtered_docs)} passed threshold {threshold}')
    return filtered_docs

def get_collection_size() -> int:
    try:
        store = get_vector_store()
        if store is None:
            return 0
        return store._collection.count()
    except Exception as e:
        logger.error(f'Error checking ChromaDB collection status: {e}')
        return 0

def delete_document_vectors(filename: str, user_id: int) -> bool:
    try:
        store = get_vector_store()
        if store is None:
            return False
        # Use $and for multi-tenant safety
        store._collection.delete(where={
            "$and": [
                {"source": filename},
                {"user_id": user_id}
            ]
        })
        logger.info(f'Purged vectors for document: {filename} (User: {user_id})')
        return True
    except Exception as e:
        logger.error(f'Vector deletion failed for {filename} (User: {user_id}): {e}')
        return False

def delete_all_user_vectors(user_id: int) -> bool:
    """Wipe all environment for a user (e.g. on account deletion)."""
    try:
        store = get_vector_store()
        if store is None:
            return False
        store._collection.delete(where={"user_id": user_id})
        logger.info(f'Purged ALL vectors for user: {user_id}')
        return True
    except Exception as e:
        logger.error(f'User vector wipe failed: {e}')
        return False
