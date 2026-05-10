import { useEffect, useRef } from "react";
import ChatMessage from "./ChatMessage";
import Loader from "./Loader";

export default function ChatWindow({ messages, isLoading, onSuggestion }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  return (
    <div className="flex-1 overflow-y-auto scrollbar-thin px-4 py-8">
      <div className="max-w-3xl mx-auto space-y-8">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <div className="w-20 h-20 rounded-3xl bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center mb-6 shadow-sm border border-blue-100">
              <svg
                className="w-10 h-10 text-blue-600"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
                />
              </svg>
            </div>
            <h2 className="text-2xl font-bold text-slate-800 mb-2">
              How can I help you today?
            </h2>
            <p className="text-slate-500 max-w-md">
              I'm your AI document assistant. Ask me anything about your
              uploaded documents.
            </p>
          </div>
        ) : (
          messages.map((msg, index) => (
            <ChatMessage key={msg.id || index} message={msg} />
          ))
        )}

        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-white border border-slate-100 rounded-2xl rounded-tl-sm shadow-sm p-4">
              <Loader />
            </div>
          </div>
        )}

        <div ref={bottomRef} className="h-4" />
      </div>
    </div>
  );
}
