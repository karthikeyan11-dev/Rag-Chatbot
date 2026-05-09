import { useState } from "react";
import TabNavigation from "./components/TabNavigation";
import DocumentUpload from "./pages/DocumentUpload";
import AIAssistant from "./pages/AIAssistant";

export default function App() {
  const [activeTab, setActiveTab] = useState("assistant");

  return (
    <div className="flex flex-col h-screen bg-[#f8fafc] font-sans selection:bg-blue-100 selection:text-blue-900">
      {/* Premium Glass Header */}
      <header className="flex-shrink-0 sticky top-0 z-50 glass-effect px-8 py-4 flex items-center justify-between border-b border-slate-200/50">
        <div className="flex items-center gap-6">
          <button className="text-slate-400 hover:text-blue-600 transition-all duration-300 transform hover:scale-110">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
          </button>
          
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-600 to-indigo-700 flex items-center justify-center shadow-lg shadow-blue-200 rotate-3 transition-transform hover:rotate-0 duration-300">
              <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <div>
              <h1 className="text-xl font-extrabold text-slate-800 tracking-tight leading-none">
                SWS AI <span className="text-blue-600 italic font-medium">PolicyHub</span>
              </h1>
              <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest mt-1">
                Enterprise Knowledge Assistant
              </p>
            </div>
          </div>
        </div>
        
        <div className="flex items-center gap-6">
          <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-100 border border-slate-200 text-[11px] font-semibold text-slate-600">
            <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
            System Status: Operational
          </div>
          
          <button className="text-slate-400 hover:text-blue-600 transition-colors relative group">
            <svg className="w-6 h-6 group-hover:scale-110 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
            </svg>
            <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-red-500 rounded-full border-2 border-white shadow-sm"></span>
          </button>
          
          <div className="w-9 h-9 rounded-full bg-gradient-to-tr from-slate-200 to-slate-100 border-2 border-white shadow-md cursor-pointer hover:shadow-lg transition-shadow"></div>
        </div>
      </header>

      {/* Tab Navigation Area */}
      <div className="flex-shrink-0 bg-white border-b border-slate-100">
        <TabNavigation activeTab={activeTab} setActiveTab={setActiveTab} />
      </div>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col min-h-0 overflow-hidden bg-[#f8fafc]">
        <div className="flex-1 flex flex-col animate-fade-in h-full">
          {activeTab === "upload" ? <DocumentUpload /> : <AIAssistant />}
        </div>
      </main>
    </div>
  );
}

