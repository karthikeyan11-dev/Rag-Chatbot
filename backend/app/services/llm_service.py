import os
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

_llm = None


def get_llm() -> ChatOpenAI:
    """Return a singleton LLM instance."""
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            openai_api_key=os.getenv("OPENAI_API_KEY"),
        )
    return _llm
