const API_BASE_URL = "http://localhost:8000/api";

const getHeaders = () => {
  const token = localStorage.getItem("auth_token");
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
};

export const sendMessage = async (question, sessionId = null) => {
  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify({
      question,
      session_id: sessionId,
    }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(
      errorData.detail || "Failed to get a response from the AI assistant.",
    );
  }

  return response.json();
};

export const uploadFiles = async (files) => {
  const formData = new FormData();
  for (let i = 0; i < files.length; i++) {
    formData.append("files", files[i]);
  }

  const token = localStorage.getItem("auth_token");
  const response = await fetch(`${API_BASE_URL}/upload`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(
      errorData.detail ||
        "Failed to upload files. Please check file format and try again.",
    );
  }

  return response.json();
};

export const getDocuments = async () => {
  const response = await fetch(`${API_BASE_URL}/documents`, {
    headers: getHeaders(),
  });
  if (!response.ok) {
    throw new Error("Failed to fetch document list from the server.");
  }
  return response.json();
};

export const getIngestionStatus = async () => {
  const response = await fetch(`${API_BASE_URL}/ingestion-status`, {
    headers: getHeaders(),
  });
  if (!response.ok) {
    throw new Error("Failed to check ingestion status.");
  }
  return response.json();
};

export const deleteDocument = async (filename) => {
  const response = await fetch(
    `${API_BASE_URL}/documents/${encodeURIComponent(filename)}`,
    {
      method: "DELETE",
      headers: getHeaders(),
    },
  );

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to delete the document.");
  }

  return response.json();
};

// --- Session Management Methods ---

export const getSessions = async () => {
  const response = await fetch(`${API_BASE_URL}/sessions`, {
    headers: getHeaders(),
  });
  if (!response.ok) {
    throw new Error("Failed to fetch chat sessions.");
  }
  return response.json();
};

export const getSessionDetail = async (sessionId) => {
  const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}`, {
    headers: getHeaders(),
  });
  if (!response.ok) {
    throw new Error("Failed to fetch chat history for this session.");
  }
  return response.json();
};

export const deleteSession = async (sessionId) => {
  const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}`, {
    method: "DELETE",
    headers: getHeaders(),
  });
  if (!response.ok) {
    throw new Error("Failed to delete chat session.");
  }
  return response.json();
};
