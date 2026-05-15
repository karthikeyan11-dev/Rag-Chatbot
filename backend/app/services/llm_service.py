import os
import json
import logging
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, SystemMessage
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)
_llm = None


def get_llm() -> ChatGoogleGenerativeAI:
    """Return a singleton Gemini LLM instance with retry logic."""
    global _llm
    if _llm is None:
        # Using gemini-3-flash-preview for production stability and higher quota limits
        _llm = ChatGoogleGenerativeAI(
            model="gemini-3-flash-preview",
            temperature=0,
            max_retries=3,
            google_api_key=os.getenv("GOOGLE_API_KEY"),
        )
    return _llm


async def classify_query_intent(query: str) -> dict:
    """
    Classify the user query intent to route the RAG pipeline.
    Intents: document_summary, factual_retrieval, analytical, comparison, followup_contextual, general_chat
    """
    llm = get_llm()
    
    prompt = f"""
    You are an intelligent query intent classifier for a document-based RAG assistant.
    Classify the user's query into EXACTLY one of the following intents:

    - document_summary: Requests a summary, overview, or "what is this about" for the uploaded documents.
    - factual_retrieval: Specific questions looking for hard facts, numbers, or specific policies.
    - analytical: Requests for analysis, reasoning, or "why" things are a certain way based on documents.
    - comparison: Comparing two or more items, policies, or sections within documents.
    - followup_contextual: Short queries like "tell me more" or "who is the author" that depend on previous context.
    - general_chat: Greetings (hi, hello) or questions unrelated to documents.

    Return ONLY a JSON object with the following keys:
    "intent": The classified intent string.
    "confidence": A float between 0 and 1.
    "reasoning": A very brief explanation.

    QUERY: "{query}"
    """
    
    try:
        # Use sync call in thread or direct async if available. LangChain ChatGoogleGenerativeAI is sync-based invoke.
        import asyncio
        response = await asyncio.to_thread(llm.invoke, [HumanMessage(content=prompt)])
        content = response.content.strip()
        
        # Robust JSON extraction
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "{" in content:
            content = content[content.find("{"):content.rfind("}")+1]
            
        data = json.loads(content)
        logger.info(f"Intent classified: {data.get('intent')} for query: {query[:50]}...")
        return data
    except Exception as e:
        logger.error(f"Intent classification failed: {e}")
        return {"intent": "factual_retrieval", "confidence": 0.5, "reasoning": "fallback due to error"}


async def generate_document_intelligence(text_sample: str) -> dict:
    """
    Generate intelligent metadata for a document based on a content sample.
    """
    llm = get_llm()
    
    prompt = f"""
    You are a document intelligence expert. Analyze the following document text sample and provide:
    1. A concise summary (2-3 sentences).
    2. A list of 5 key topics or themes.
    3. The likely document type (e.g., Policy, Report, Invoice, Correspondence).

    SAMPLE TEXT:
    {text_sample[:4000]}

    Return ONLY a JSON object with keys: "summary", "key_topics", "document_type".
    """
    
    try:
        import asyncio
        response = await asyncio.to_thread(llm.invoke, [HumanMessage(content=prompt)])
        content = response.content.strip()
        
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "{" in content:
            content = content[content.find("{"):content.rfind("}")+1]
            
        data = json.loads(content)
        return data
    except Exception as e:
        logger.error(f"Document intelligence generation failed: {e}")
        return {
            "summary": "Summary unavailable.",
            "key_topics": "none",
            "document_type": "Unknown"
        }

