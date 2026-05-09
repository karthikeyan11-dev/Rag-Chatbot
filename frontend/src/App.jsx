import { useState, useRef, useCallback } from "react";
import DocumentUpload from "./pages/DocumentUpload";
import AIAssistant from "./pages/AIAssistant";
import ChatSidebar from "./components/ChatSidebar";
import { getSessions } from "./services/api";

export default function App() {
  const [activeTab, setActiveTab] = useState("assistant");
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const assistantRef = useRef(null);

  const fetchSessions = useCallback(async () => {
    try {
      const data = await getSessions();
      setSessions(data);
    } catch (err) {
      console.error("Error fetching sessions:", err);
    }
  }, []);

  const handleNewChat = () => {
    setActiveSessionId(null);
    setActiveTab("assistant");
    if (assistantRef.current) {
      assistantRef.current.handleNewChat();
    }
  };

  const handleSelectSession = (sessionId) => {
    setActiveSessionId(sessionId);
    setActiveTab("assistant");
    if (assistantRef.current) {
      assistantRef.current.handleSelectSession(sessionId);
    }
  };

  const handleDeleteSession = async (sessionId) => {
    if (assistantRef.current) {
      await assistantRef.current.handleDeleteSession(sessionId);
    }
  };

  return (
    <div className="flex flex-row h-screen bg-[#f8fafc] font-sans selection:bg-blue-100 selection:text-blue-900 overflow-hidden">
      {/* ChatGPT-style Sidebar */}
      <ChatSidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        sessions={sessions}
        activeSessionId={activeSessionId}
        onNewChat={handleNewChat}
        onSelectSession={handleSelectSession}
        onDeleteSession={handleDeleteSession}
        fetchSessions={fetchSessions}
      />

      <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
        {/* Premium Glass Header */}
        <header className="flex-shrink-0 sticky top-0 z-50 glass-effect px-8 py-4 flex items-center justify-between border-b border-slate-200/50">
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-600 to-indigo-700 flex items-center justify-center shadow-lg shadow-blue-200 rotate-3 transition-transform hover:rotate-0 duration-300">
                <svg
                  className="w-6 h-6 text-white"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.5"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  />
                </svg>
              </div>
              <div>
                <h1 className="text-xl font-extrabold text-slate-800 tracking-tight leading-none">
                  SWS AI{" "}
                  <span className="text-blue-600 italic font-medium">
                    PolicyHub
                  </span>
                </h1>
                <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest mt-1">
                  Enterprise Knowledge Assistant
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-6">
            <button className="text-slate-400 hover:text-blue-600 transition-colors relative group">
              <svg
                className="w-6 h-6 group-hover:scale-110 transition-transform"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
                />
              </svg>
              <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-red-500 rounded-full border-2 border-white shadow-sm"></span>
            </button>
            <div className="w-9 h-9 rounded-full bg-gradient-to-tr from-slate-200 to-slate-100 border-2 border-white shadow-md cursor-pointer hover:shadow-lg transition-shadow"></div>
          </div>
        </header>

        {/* Main Content Area */}
        <main className="flex-1 flex flex-col min-h-0 overflow-hidden bg-[#f8fafc]">
          <div className="flex-1 flex flex-col animate-fade-in h-full">
            {activeTab === "upload" ? (
              <DocumentUpload />
            ) : (
              <AIAssistant
                ref={assistantRef}
                fetchSessions={fetchSessions}
                onSessionCreated={(id) => setActiveSessionId(id)}
              />
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
