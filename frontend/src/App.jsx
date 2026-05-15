import { useState, useRef, useCallback, useEffect } from "react";
import DocumentUpload from "./pages/DocumentUpload";
import AIAssistant from "./pages/AIAssistant";
import ChatSidebar from "./components/ChatSidebar";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import { getSessions } from "./services/api";

export default function App() {
  const [user, setUser] = useState(null);
  const [authMode, setAuthMode] = useState("login"); // login, signup
  const [activeTab, setActiveTab] = useState("assistant");
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const assistantRef = useRef(null);

  // Check for existing session on mount
  useEffect(() => {
    const savedUser = localStorage.getItem("user");
    const token = localStorage.getItem("auth_token");
    if (savedUser && token) {
      setUser(JSON.parse(savedUser));
    }
  }, []);

  const handleLogin = (data) => {
    localStorage.setItem("auth_token", data.access_token);
    localStorage.setItem("user", JSON.stringify(data.user));
    setUser(data.user);
  };

  const handleLogout = () => {
    localStorage.removeItem("auth_token");
    localStorage.removeItem("user");
    setUser(null);
    setSessions([]);
    setActiveSessionId(null);
  };

  const fetchSessions = useCallback(async () => {
    if (!user) return;
    try {
      const data = await getSessions();
      setSessions(data);
    } catch (err) {
      console.error("Error fetching sessions:", err);
    }
  }, [user]);

  const handleNewChat = () => {
    setActiveSessionId(null);
    setActiveTab("assistant");
    if (assistantRef.current) {
      assistantRef.current.handleNewChat();
    }
  };

  const handleSelectSession = (sessionId) => {
    setActiveTab("assistant");
    setActiveSessionId(sessionId);
    // Removed imperative call as useEffect handles it
  };

  const handleDeleteSession = async (sessionId) => {
    if (assistantRef.current) {
      await assistantRef.current.handleDeleteSession(sessionId);
    }
  };

  if (!user) {
    return authMode === "login" ? (
      <Login
        onLogin={handleLogin}
        onSwitchToSignup={() => setAuthMode("signup")}
      />
    ) : (
      <Signup
        onSignupSuccess={() => setAuthMode("login")}
        onSwitchToLogin={() => setAuthMode("login")}
      />
    );
  }

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
        onLogout={handleLogout}
        user={user}
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
                    DocuHub
                  </span>
                </h1>
                <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest mt-1">
                  Cross-Domain RAG Assistant
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-6">
            <div className="w-9 h-9 rounded-full bg-gradient-to-br from-blue-600 to-blue-700 border-2 border-white shadow-md flex items-center justify-center text-sm font-bold text-white uppercase transform transition-transform hover:scale-105 cursor-pointer">
              {user?.full_name?.charAt(0) || user?.username?.charAt(0) || "U"}
            </div>
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
                activeSessionId={activeSessionId}
                setActiveSessionId={setActiveSessionId}
              />
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
