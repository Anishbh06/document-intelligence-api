"use client";

import { FormEvent, useMemo, useState } from "react";
import { useParams } from "next/navigation";

import ChatMessage from "@/components/ChatMessage";
import Loader from "@/components/Loader";
import { queryDocument } from "@/lib/api";
import { Citation } from "@/lib/types";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
}

export default function DocChatPage() {
  const params = useParams();
  const documentId = Number(params.doc_id);

  const [messages, setMessages] = useState<Message[]>([]);
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canAsk = useMemo(
    () => !isNaN(documentId) && documentId > 0 && !asking,
    [documentId, asking]
  );

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!question.trim() || !canAsk) return;

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: question.trim(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setQuestion("");
    setError(null);
    setAsking(true);

    try {
      const response = await queryDocument(documentId, userMessage.content);
      const assistantMessage: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: response.answer,
        citations: response.citations,
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to query document."
      );
    } finally {
      setAsking(false);
    }
  };

  return (
    <section className="mx-auto mt-6 max-w-4xl">
      <div className="rounded-3xl bg-white p-6 shadow-soft">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 pb-4">
          <div>
            <p className="text-xs uppercase tracking-wide text-slate-500">
              Document Chat
            </p>
            <h1 className="text-xl font-semibold text-slate-900">
              Document #{documentId}
            </h1>
          </div>
          <span className="inline-flex rounded-full bg-emerald-100 px-3 py-1 text-xs font-medium capitalize text-emerald-800">
            ready
          </span>
        </div>

        <div className="mt-6 h-[55vh] space-y-4 overflow-y-auto rounded-2xl border border-slate-200 bg-slate-50 p-4">
          {messages.length === 0 && (
            <p className="text-sm text-slate-500">
              Ask your first question about this document.
            </p>
          )}
          {messages.map((message) => (
            <ChatMessage
              key={message.id}
              role={message.role}
              content={message.content}
              citations={message.citations}
            />
          ))}
          {asking && <Loader label="Generating answer..." />}
        </div>

        <form onSubmit={handleSubmit} className="mt-4 space-y-3">
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            disabled={!canAsk}
            rows={3}
            placeholder={
              canAsk
                ? "Ask anything about the uploaded document..."
                : "Document not available for chat."
            }
            className="w-full rounded-2xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-slate-900"
          />
          <div className="flex items-center justify-between">
            <p className="text-xs text-slate-500">Document ID: {documentId}</p>
            <button
              type="submit"
              disabled={!canAsk || !question.trim()}
              className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Send
            </button>
          </div>
        </form>

        {error && <p className="mt-4 text-sm text-rose-600">{error}</p>}
      </div>
    </section>
  );
}
