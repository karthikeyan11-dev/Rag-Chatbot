from langchain.schema import HumanMessage, SystemMessage
from app.services.vector_store import similarity_search, get_collection_size
from app.services.llm_service import get_llm
from app.utils.prompt_template import build_system_prompt

TOP_K = 4


def get_answer(question: str) -> dict:
    """
    Full RAG pipeline:
    1. Check if documents exist in the vector store
    2. Retrieve top-k relevant chunks from ChromaDB
    3. Build grounded prompt with retrieved context
    4. Call LLM and return answer + source documents
    """
    # CASE 1: Check if documents are uploaded
    if get_collection_size() == 0:
        return {
            "answer": "No company documents have been uploaded yet. Please upload documents to start using the RAG assistant.",
            "sources": [],
        }

    # STEP 2: Similarity search
    docs = similarity_search(question, top_k=TOP_K)

    # STEP 3: Handle empty retrieval
    if not docs:
        return {
            "answer": "I don't have that information in the uploaded company documents.",
            "sources": [],
        }

    # Build context string from retrieved chunks
    context_parts = []
    for doc in docs:
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

    try:
        response = llm.invoke(messages)
        answer = response.content.strip()

        # Final check: if LLM says it doesn't know (should match prompt rules)
        if "I don't have that information" in answer:
             return {
                "answer": "I don't have that information in the uploaded company documents.",
                "sources": [],
            }

        return {
            "answer": answer,
            "sources": sources,
        }
    except Exception as e:
        print(f"LLM Error: {e}")
        return {
            "answer": "I encountered an error while trying to answer your question. Please try again.",
            "sources": [],
        }
