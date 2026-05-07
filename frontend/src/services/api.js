const API_BASE_URL = "/api";

/**
 * Send a question to the RAG chatbot backend.
 * @param {string} question
 * @returns {Promise<{ answer: string, sources: string[] }>}
 */
export async function sendMessage(question) {
  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ question }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Server error: ${response.status}`);
  }

  return response.json();
}
