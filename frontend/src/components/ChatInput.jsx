import { useState, useEffect } from "react";

export default function ChatInput({ onSend, isLoading, value: externalValue, onChange }) {
  const [internalValue, setInternalValue] = useState("");
  
  // Sync with external value if provided (for suggestions)
  useEffect(() => {
    if (externalValue !== undefined) {
      setInternalValue(externalValue);
    }
  }, [externalValue]);

  const handleTextChange = (e) => {
    const newVal = e.target.value;
    setInternalValue(newVal);
    if (onChange) onChange(newVal);
    
    // Auto-resize textarea
    e.target.style.height = "auto";
    e.target.style.height = Math.min(e.target.scrollHeight, 160) + "px";
  };

  const handleSubmit = () => {
    const trimmed = internalValue.trim();
    if (!trimmed || isLoading) return;
    onSend(trimmed);
    setInternalValue("");
    if (onChange) onChange("");
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="border-t border-slate-100 bg-white px-6 py-6 shadow-[0_-4px_20px_-10px_rgba(0,0,0,0.05)]">
      <div className="max-w-3xl mx-auto">
        <div className="relative flex items-center group">
          <textarea
            value={internalValue}
            onChange={handleTextChange}
            onKeyDown={handleKeyDown}
            placeholder="Ask about policies, leave, benefits..."
            disabled={isLoading}
            rows={1}
            className="w-full resize-none rounded-2xl border border-slate-200 bg-slate-50 px-6 py-4 pr-16 text-[15px] text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent focus:bg-white disabled:opacity-50 disabled:cursor-not-allowed leading-relaxed transition-all duration-200 shadow-inner"
            style={{
              height: "auto",
              minHeight: "56px",
              maxHeight: "160px",
            }}
          />
          <button
            onClick={handleSubmit}
            disabled={!internalValue.trim() || isLoading}
            className="absolute right-3 w-10 h-10 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:bg-slate-200 disabled:cursor-not-allowed text-white flex items-center justify-center transition-all duration-200 shadow-md shadow-blue-100 active:scale-95"
            aria-label="Send message"
          >
            {isLoading ? (
              <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            ) : (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
              </svg>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
