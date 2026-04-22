type ChatRole = "user" | "assistant";

interface ChatMessageProps {
  role: ChatRole;
  content: string;
  citations?: { id: number; content: string }[];
}

export default function ChatMessage({ role, content, citations }: ChatMessageProps) {
  const isUser = role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm shadow-soft ${
          isUser ? "bg-slate-900 text-white" : "bg-white text-slate-800"
        }`}
      >
        <p className="whitespace-pre-wrap">{content}</p>
        {!isUser && citations && citations.length > 0 && (
          <div className="mt-3 space-y-2 border-t border-slate-200 pt-3">
            <p className="text-xs font-medium text-slate-500">Sources</p>
            {citations.slice(0, 3).map((citation) => (
              <p key={citation.id} className="text-xs text-slate-600">
                {citation.content.slice(0, 160)}...
              </p>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
