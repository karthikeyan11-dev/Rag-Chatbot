from langchain.schema import HumanMessage, SystemMessage
from app.services.vector_store import similarity_search
from app.services.llm_service import get_llm
from app.utils.prompt_template import build_system_prompt

TOP_K = 4


def get_answer(question: str) -> dict:
    """
    Full RAG pipeline:
    1. Retrieve top-k relevant chunks from ChromaDB
    2. Build grounded prompt with retrieved context
    3. Call LLM and return answer + source documents
    """
    docs = similarity_search(question, top_k=TOP_K)

    if not docs:
        return {
            "answer": "I don't have that information in the company documents.",
            "sources": [],
        }

    # Build context string from retrieved chunks
    context_parts = []
    for i, doc in enumerate(docs):
        source = doc.metadata.get("source", "Unknown")
        page = doc.metadata.get("page", "?")
        context_parts.append(f"[Source: {source}, Page {page}]\n{doc.page_content}")

    context = "\n\n---\n\n".join(context_parts)

    # Collect unique source document names
    sources = list({doc.metadata.get("source", "Unknown") for doc in docs})
    sources.sort()

    # Build messages
    system_prompt = build_system_prompt(context)
    llm = get_llm()

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=question),
    ]

    response = llm.invoke(messages)
    answer = response.content.strip()

    return {
        "answer": answer,
        "sources": sources,
    }
