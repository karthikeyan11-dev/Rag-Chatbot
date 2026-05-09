import os
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

load_dotenv()

_llm = None


def get_llm() -> ChatGoogleGenerativeAI:
    """Return a singleton Gemini LLM instance with retry logic."""
    global _llm
    if _llm is None:
        _llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            temperature=0,
            max_retries=5,
            google_api_key=os.getenv("GOOGLE_API_KEY"),
        )
    return _llm
