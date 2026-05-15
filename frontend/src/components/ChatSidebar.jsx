import React, { useEffect, useState } from "react";

export default function ChatSidebar({
  activeTab,
  setActiveTab,
  sessions,
  activeSessionId,
  onNewChat,
  onSelectSession,
  onDeleteSession,
  fetchSessions,
  onLogout,
  user,
}) {
  const [showLogoutConfirm, setShowLogoutConfirm] = useState(false);

  useEffect(() => {
    // Only fetch if sessions is empty or we specifically need a refresh
    if (fetchSessions && sessions.length === 0) {
      fetchSessions();
    }
  }, [fetchSessions]); // Remove sessions from dependency to prevent loop

  const navItems = [
    {
      id: "assistant",
      name: "AI Assistant",
      icon: (
        <svg
          className="w-4 h-4"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="2.5"
            d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
          />
        </svg>
      ),
    },
    {
      id: "upload",
      name: "Knowledge Base",
      icon: (
        <svg
          className="w-4 h-4"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="2.5"
            d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
          />
        </svg>
      ),
    },
  ];

  const handleLogoutClick = () => {
    setShowLogoutConfirm(true);
  };

  return (
    <aside className="w-72 bg-[#0f172a] flex flex-col h-full text-slate-300 border-r border-slate-800 relative z-20">
      {/* Logout Confirmation Modal */}
      {showLogoutConfirm && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl p-6 w-full max-w-sm transform animate-in zoom-in-95 duration-200">
            <div className="flex items-center justify-center w-12 h-12 rounded-full bg-red-500/10 text-red-500 mb-4 mx-auto">
              <svg
                className="w-6 h-6"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
                />
              </svg>
            </div>

            <h3 className="text-lg font-bold text-white text-center mb-2">
              Confirm Logout
            </h3>
            <p className="text-slate-400 text-sm text-center mb-6">
              Are you sure you want to log out of your account? You will need to
              sign in again to access your chats.
            </p>

            <div className="flex gap-3">
              <button
                onClick={() => setShowLogoutConfirm(false)}
                className="flex-1 px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm font-semibold transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  setShowLogoutConfirm(false);
                  onLogout();
                }}
                className="flex-1 px-4 py-2.5 rounded-xl bg-red-600 hover:bg-red-500 text-white text-sm font-semibold shadow-lg shadow-red-900/20 transition-all active:scale-95"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Navigation Options - TOP */}
      <div className="p-3 space-y-1">
        <div className="px-3 mb-2">
          <span className="text-[10px] font-black uppercase tracking-widest text-slate-500">
            Menu
          </span>
        </div>
        {navItems.map((item) => (
          <button
            key={item.id}
            onClick={() => setActiveTab(item.id)}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 text-sm font-bold ${
              activeTab === item.id
                ? "bg-blue-600/10 text-blue-400 border border-blue-500/20 shadow-sm"
                : "text-slate-400 hover:bg-slate-800/50 hover:text-slate-200"
            }`}
          >
            <span
              className={
                activeTab === item.id ? "text-blue-400" : "text-slate-500"
              }
            >
              {item.icon}
            </span>
            {item.name}
          </button>
        ))}
      </div>

      {/* Sessions List - MIDDLE */}
      <div className="flex-1 overflow-y-auto px-3 py-2 space-y-1 custom-scrollbar border-t border-slate-800/50 mt-2">
        <div className="px-3 mb-2 mt-2">
          <span className="text-[10px] font-black uppercase tracking-widest text-slate-500">
            Chat History
          </span>
        </div>

        {sessions.length === 0 ? (
          <div className="px-4 py-8 text-center">
            <p className="text-xs text-slate-600 italic">
              No previous chats found.
            </p>
          </div>
        ) : (
          sessions.map((session) => (
            <div
              key={session.id}
              className={`group flex items-center gap-3 px-3 py-3 rounded-lg cursor-pointer transition-all duration-200 relative ${
                activeSessionId === session.id
                  ? "bg-slate-800/80 text-white shadow-md border border-slate-700"
                  : "hover:bg-slate-800/40 hover:text-slate-200"
              }`}
              onClick={() => onSelectSession(session.id)}
            >
              <svg
                className={`w-4 h-4 flex-shrink-0 ${activeSessionId === session.id ? "text-blue-400" : "text-slate-600 group-hover:text-slate-400"}`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
                />
              </svg>

              <span className="text-sm font-medium truncate flex-1 pr-6">
                {session.title || "New Chat"}
              </span>

              {/* Delete Action */}
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDeleteSession(session.id);
                }}
                className={`absolute right-2 opacity-0 group-hover:opacity-100 p-1 rounded-md hover:bg-slate-700 hover:text-red-400 transition-all duration-200 ${activeSessionId === session.id ? "opacity-40" : ""}`}
              >
                <svg
                  className="w-3.5 h-3.5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                  />
                </svg>
              </button>
            </div>
          ))
        )}
      </div>

      {/* Footer & New Chat - BOTTOM */}
      <div className="p-4 bg-[#0f172a] border-t border-slate-800 relative">
        <button
          onClick={onNewChat}
          className="absolute -top-7 right-4 w-12 h-12 rounded-full bg-blue-600 hover:bg-blue-500 text-white shadow-xl shadow-blue-900/40 flex items-center justify-center transition-all duration-300 hover:scale-110 active:scale-95 group z-30"
          title="New Chat"
        >
          <svg
            className="w-6 h-6 transform transition-transform group-hover:rotate-90 duration-300"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2.5"
              d="M12 4v16m8-8H4"
            />
          </svg>
        </button>

        <div className="flex items-center gap-3 py-1">
          <div className="w-9 h-9 rounded-full bg-gradient-to-br from-slate-700 to-slate-800 border border-slate-700 flex items-center justify-center text-xs font-bold text-white overflow-hidden shadow-inner">
            <div className="w-full h-full bg-blue-600/20 flex items-center justify-center text-blue-400 capitalize">
              {user?.full_name?.charAt(0) || user?.username?.charAt(0) || "U"}
            </div>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-bold text-white truncate text-opacity-90">
              {user?.full_name || user?.username || "Guest User"}
            </p>
            <p className="text-[10px] text-blue-400/80 font-black uppercase tracking-widest mt-0.5">
              Verified
            </p>
          </div>
          <button
            onClick={handleLogoutClick}
            className="p-1.5 hover:bg-red-500/20 text-slate-400 hover:text-red-400 rounded-lg transition-colors group"
            title="Logout"
          >
            <svg
              className="w-5 h-5 group-hover:scale-110 transition-transform"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
              />
            </svg>
          </button>
        </div>
      </div>
    </aside>
  );
}
