const API_BASE_URL = "http://localhost:8000/api";

export const sendMessage = async (question, sessionId = null) => {
  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ 
      question,
      session_id: sessionId 
    }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to get a response from the AI assistant.");
  }

  return response.json();
};

export const uploadFiles = async (files) => {
  const formData = new FormData();
  for (let i = 0; i < files.length; i++) {
    formData.append("files", files[i]);
  }

  const response = await fetch(`${API_BASE_URL}/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to upload files. Please check file format and try again.");
  }

  return response.json();
};

export const getDocuments = async () => {
  const response = await fetch(`${API_BASE_URL}/documents`);
  if (!response.ok) {
    throw new Error("Failed to fetch document list from the server.");
  }
  return response.json();
};

export const getIngestionStatus = async () => {
  const response = await fetch(`${API_BASE_URL}/ingestion-status`);
  if (!response.ok) {
    throw new Error("Failed to check ingestion status.");
  }
  return response.json();
};

export const deleteDocument = async (filename) => {
  const response = await fetch(`${API_BASE_URL}/documents/${encodeURIComponent(filename)}`, {
    method: "DELETE",
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to delete the document.");
  }

  return response.json();
};

// --- Session Management Methods ---

export const getSessions = async () => {
  const response = await fetch(`${API_BASE_URL}/sessions`);
  if (!response.ok) {
    throw new Error("Failed to fetch chat sessions.");
  }
  return response.json();
};

export const getSessionDetail = async (sessionId) => {
  const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}`);
  if (!response.ok) {
    throw new Error("Failed to fetch chat history for this session.");
  }
  return response.json();
};

export const deleteSession = async (sessionId) => {
  const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    throw new Error("Failed to delete chat session.");
  }
  return response.json();
};
