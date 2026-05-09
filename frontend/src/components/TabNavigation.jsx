import React from "react";

export default function TabNavigation({ activeTab, setActiveTab }) {
  const tabs = [
    { id: "assistant", name: "AI Assistant", icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
      </svg>
    )},
    { id: "upload", name: "Knowledge Base", icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
      </svg>
    )},
  ];

  return (
    <div className="flex justify-center bg-white/50 backdrop-blur-sm">
      <div className="flex gap-2 p-1.5 my-2 bg-slate-100/80 rounded-2xl border border-slate-200/50">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2.5 py-2 px-6 rounded-xl transition-all duration-300 text-sm font-bold tracking-tight ${
              activeTab === tab.id
                ? "bg-white text-blue-600 shadow-sm border border-slate-200/50 scale-[1.02]"
                : "text-slate-500 hover:text-slate-800 hover:bg-slate-200/50"
            }`}
          >
            <span className={activeTab === tab.id ? "text-blue-600" : "text-slate-400"}>
              {tab.icon}
            </span>
            {tab.name}
          </button>
        ))}
      </div>
    </div>
  );
}
