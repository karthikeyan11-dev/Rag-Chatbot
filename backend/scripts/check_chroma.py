import os
import sys

# Add parent directory to path to allow importing app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.vector_store import get_vector_store

def check_chroma():
    print("Checking ChromaDB status...")
    store = get_vector_store()
    if store is None:
        print("Failed to initialize vector store.")
        return
    
    count = store._collection.count()
    print(f"Total documents in collection: {count}")
    
    if count > 0:
        # Get one sample
        sample = store._collection.get(limit=1)
        print("\nSample Metadata:")
        print(sample['metadatas'][0])
        print("\nSample Text (first 100 chars):")
        print(sample['documents'][0][:100])

if __name__ == "__main__":
    check_chroma()
