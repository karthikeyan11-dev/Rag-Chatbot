import SourceList from "./SourceList";

export default function ChatMessage({ message }) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[75%] px-4 py-3 rounded-2xl rounded-tr-sm bg-blue-600 text-white text-sm leading-relaxed shadow-sm">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start">
      <div className="max-w-[80%]">
        <div className="flex items-center gap-2 mb-1.5 ml-1">
          <div className="w-5 h-5 rounded-full bg-blue-600 flex items-center justify-center flex-shrink-0">
            <svg
              className="w-3 h-3 text-white"
              viewBox="0 0 16 16"
              fill="currentColor"
            >
              <path d="M8 1a7 7 0 100 14A7 7 0 008 1zm0 2a1.5 1.5 0 110 3 1.5 1.5 0 010-3zm0 9.5c-2 0-3.5-1-3.5-2.25 0-.83 1.57-1.25 3.5-1.25s3.5.42 3.5 1.25C11.5 11.5 10 12.5 8 12.5z" />
            </svg>
          </div>
          <span className="text-xs font-semibold text-blue-700">
            Policy Assistant
          </span>
        </div>
        <div className="px-4 py-3 rounded-2xl rounded-tl-sm bg-white border border-slate-200 text-sm text-slate-700 leading-relaxed shadow-sm">
          {message.content}
          {message.sources && message.sources.length > 0 && (
            <SourceList sources={message.sources} />
          )}
        </div>
      </div>
    </div>
  );
}
