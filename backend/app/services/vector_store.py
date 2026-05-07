import os
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv

load_dotenv()

CHROMA_PERSIST_DIR = os.path.join(os.path.dirname(__file__), "..", "db", "chroma_db")
CHROMA_PERSIST_DIR = os.path.abspath(CHROMA_PERSIST_DIR)

COLLECTION_NAME = "company_policies"

_vector_store = None


def get_vector_store() -> Chroma:
    """Return a singleton ChromaDB vector store instance."""
    global _vector_store
    if _vector_store is None:
        os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
        embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=os.getenv("OPENAI_API_KEY"),
        )
        _vector_store = Chroma(
            collection_name=COLLECTION_NAME,
            embedding_function=embeddings,
            persist_directory=CHROMA_PERSIST_DIR,
        )
        print(f"ChromaDB initialized at: {CHROMA_PERSIST_DIR}")
    return _vector_store


def similarity_search(query: str, top_k: int = 4):
    """Perform similarity search and return top_k documents."""
    store = get_vector_store()
    return store.similarity_search(query, k=top_k)
