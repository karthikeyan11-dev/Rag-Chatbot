import React, { useState, useEffect } from "react";
import ChatWindow from "../components/ChatWindow";
import ChatInput from "../components/ChatInput";
import { sendMessage, getDocuments } from "../services/api";

export default function AIAssistant() {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [hasDocs, setHasDocs] = useState(true);

  useEffect(() => {
    const checkDocs = async () => {
      try {
        const data = await getDocuments();
        setHasDocs(data.documents && data.documents.length > 0);
      } catch (err) {
        console.error("Error checking documents:", err);
      }
    };
    checkDocs();
  }, []);

  const handleSend = async (question) => {
    if (!question.trim() || isLoading) return;

    setError(null);

    const userMessage = {
      id: Date.now(),
      role: "user",
      content: question,
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const data = await sendMessage(question);

      const assistantMessage = {
        id: Date.now() + 1,
        role: "assistant",
        content: data.answer,
        sources: data.sources,
      };

      setMessages((prev) => [...prev, assistantMessage]);
      
      // Update hasDocs state based on response content if needed
      if (data.answer.includes("No company documents have been uploaded yet")) {
        setHasDocs(false);
      } else {
        setHasDocs(true);
      }
    } catch (err) {
      setError(err.message || "Something went wrong. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleClear = () => {
    setMessages([]);
    setError(null);
  };

  return (
    <div className="flex-1 flex flex-col min-h-0 bg-slate-50 relative">
      {/* Banner */}
      {!hasDocs ? (
        <div className="flex-shrink-0 bg-amber-50 border-b border-amber-100 px-4 py-3">
          <div className="max-w-3xl mx-auto flex items-center gap-3 text-sm font-medium text-amber-800">
            <svg className="w-5 h-5 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <div>
              <p>No company documents detected.</p>
              <p className="text-xs font-normal opacity-80">Please upload PDF documents in the "Document Upload" tab to enable the RAG assistant.</p>
            </div>
          </div>
        </div>
      ) : (
        <div className="flex-shrink-0 bg-purple-50 border-b border-purple-100 px-4 py-2">
          <div className="max-w-3xl mx-auto flex items-center justify-center gap-2 text-xs font-medium text-purple-700">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Powered by Gemini 1.5 & SWS AI company documents. Ask anything about company policies.
          </div>
        </div>
      )}

      {/* Error Banner */}
      {error && (
        <div className="flex-shrink-0 bg-red-50 border-b border-red-200 px-4 py-2">
          <div className="max-w-3xl mx-auto flex items-center justify-between gap-3">
            <div className="flex items-center gap-2 text-sm text-red-700">
              <svg className="w-4 h-4 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
              {error}
            </div>
            <button onClick={() => setError(null)} className="text-red-400 hover:text-red-600 text-lg leading-none">×</button>
          </div>
        </div>
      )}

      {/* Chat Area */}
      <ChatWindow
        messages={messages}
        isLoading={isLoading}
        onSuggestion={handleSend}
      />

      {/* Input */}
      <div className="flex-shrink-0">
        <ChatInput onSend={handleSend} isLoading={isLoading} />
      </div>

      {messages.length > 0 && (
        <button
          onClick={handleClear}
          className="absolute top-14 right-8 text-xs text-slate-400 hover:text-slate-600 transition-colors px-2 py-1 rounded hover:bg-slate-200 bg-slate-100 shadow-sm"
        >
          Clear chat
        </button>
      )}
    </div>
  );
}
