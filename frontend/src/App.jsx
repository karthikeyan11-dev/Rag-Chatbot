import { useState } from "react";
import TabNavigation from "./components/TabNavigation";
import DocumentUpload from "./pages/DocumentUpload";
import AIAssistant from "./pages/AIAssistant";

export default function App() {
  const [activeTab, setActiveTab] = useState("assistant");

  return (
    <div className="flex flex-col h-screen bg-white font-sans">
      {/* Top Header */}
      <header className="flex-shrink-0 bg-white border-b border-slate-100 px-8 py-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button className="text-slate-400 hover:text-slate-600 transition-colors">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
          </button>
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-blue-600 flex items-center justify-center shadow-blue-200 shadow-lg">
              <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <h1 className="text-xl font-bold text-slate-800 tracking-tight">
              SWS AI Document Hub <span className="ml-2 px-2 py-0.5 rounded text-[10px] bg-blue-50 text-blue-600 border border-blue-100 uppercase font-extrabold tracking-widest">Live Demo</span>
            </h1>
          </div>
        </div>
        
        <div className="flex items-center gap-5">
          <button className="text-slate-400 hover:text-slate-600 transition-colors relative">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
            </svg>
            <span className="absolute top-0 right-0 w-2 h-2 bg-red-500 rounded-full border-2 border-white"></span>
          </button>
          <div className="w-8 h-8 rounded-full bg-slate-200 border-2 border-slate-100"></div>
        </div>
      </header>

      {/* Tab Navigation */}
      <TabNavigation activeTab={activeTab} setActiveTab={setActiveTab} />

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col min-h-0 overflow-hidden">
        {activeTab === "upload" ? <DocumentUpload /> : <AIAssistant />}
      </main>
    </div>
  );
}

