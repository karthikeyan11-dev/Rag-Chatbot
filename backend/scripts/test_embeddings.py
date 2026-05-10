import os
import sys
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

load_dotenv()

from langchain_google_genai import GoogleGenerativeAIEmbeddings

def test_embeddings():
    print("Testing Google Generative AI Embeddings...")
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("Error: GOOGLE_API_KEY not found in environment.")
        return
    
    try:
        embeddings = GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-2",
            google_api_key=api_key,
            task_type="retrieval_document"
        )
        
        text = "This is a test document for embedding."
        vector = embeddings.embed_query(text)
        
        print(f"Successfully generated embedding.")
        print(f"Vector dimension: {len(vector)}")
        print(f"First 5 values: {vector[:5]}")
    except Exception as e:
        print(f"Embedding failed: {e}")

if __name__ == "__main__":
    test_embeddings()
