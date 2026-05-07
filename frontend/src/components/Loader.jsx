export default function Loader() {
  return (
    <div className="flex items-center gap-1.5 px-4 py-3">
      <span className="text-sm text-blue-500 font-medium mr-1">Thinking</span>
      <span
        className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-bounce"
        style={{ animationDelay: "0ms" }}
      />
      <span
        className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-bounce"
        style={{ animationDelay: "150ms" }}
      />
      <span
        className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-bounce"
        style={{ animationDelay: "300ms" }}
      />
    </div>
  );
}
