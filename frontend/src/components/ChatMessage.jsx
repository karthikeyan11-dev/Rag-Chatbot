import SourceList from "./SourceList";

export default function ChatMessage({ message }) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] px-5 py-3 rounded-3xl rounded-tr-sm bg-blue-600 text-white text-[15px] leading-relaxed shadow-lg shadow-blue-100">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start">
      <div className="max-w-[85%] group">
        <div className="flex items-center gap-2.5 mb-2 ml-1">
          <div className="w-6 h-6 rounded-lg bg-blue-600 flex items-center justify-center flex-shrink-0 shadow-sm">
            <svg className="w-3.5 h-3.5 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
              <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
          </div>
          <span className="text-xs font-bold text-slate-800 uppercase tracking-tight">
            AI Assistant
          </span>
        </div>
        <div className="px-6 py-4 rounded-3xl rounded-tl-sm bg-white border border-slate-100 text-[15px] text-slate-700 leading-relaxed shadow-sm group-hover:shadow-md transition-shadow">
          <div className="whitespace-pre-wrap">{message.content}</div>
          {message.sources && message.sources.length > 0 && (
            <SourceList sources={message.sources} />
          )}
        </div>
      </div>
    </div>
  );
}

