import os
from langchain_qdrant import QdrantVectorStore
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from qdrant_client import QdrantClient
from dotenv import load_dotenv

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION_NAME = "company_policies"
VECTOR_SIZE = 3072 # Gemini Embedding 2 dimension

_vector_store = None
_client = None

def get_qdrant_client() -> QdrantClient:
    """Return a singleton QdrantClient instance."""
    global _client
    if _client is None:
        _client = QdrantClient(url=QDRANT_URL)
    return _client

def get_vector_store() -> QdrantVectorStore:
    """Return a singleton Qdrant vector store instance."""
    global _vector_store
    if _vector_store is None:
        embeddings = GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-2",
            google_api_key=os.getenv("GOOGLE_API_KEY"),
        )
        
        client = get_qdrant_client()
        
        # Ensure collection exists
        try:
            if not client.collection_exists(COLLECTION_NAME):
                from qdrant_client.http import models as rest_models
                client.create_collection(
                    collection_name=COLLECTION_NAME,
                    vectors_config=rest_models.VectorParams(
                        size=VECTOR_SIZE, 
                        distance=rest_models.Distance.COSINE
                    ),
                )
                print(f"Created Qdrant collection: {COLLECTION_NAME}")
        except Exception as e:
            print(f"Note: Collection existence check/creation failed: {e}")

        _vector_store = QdrantVectorStore(
            client=client,
            collection_name=COLLECTION_NAME,
            embedding=embeddings,
        )
        print(f"Qdrant Vector Store initialized at: {QDRANT_URL}")
    return _vector_store

def reset_vector_store():
    """Reset the singleton instance."""
    global _vector_store
    _vector_store = None

def similarity_search(query: str, top_k: int = 4):
    """Perform similarity search and return top_k documents."""
    store = get_vector_store()
    return store.similarity_search(query, k=top_k)

def get_collection_size() -> int:
    """Return the number of documents in the collection."""
    client = get_qdrant_client()
    try:
        if not client.collection_exists(COLLECTION_NAME):
            return 0
        collection_info = client.get_collection(COLLECTION_NAME)
        return collection_info.points_count
    except Exception as e:
        print(f"Error getting Qdrant collection size: {e}")
        return 0
