"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import Loader from "@/components/Loader";
import { deleteDocument, getDocuments } from "@/lib/api";
import { DocumentResponse } from "@/lib/types";

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadDocuments = async () => {
    try {
      setLoading(true);
      const result = await getDocuments();
      setDocuments(result.documents);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not load documents."
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadDocuments();
  }, []);

  const handleDelete = async (id: number, filename: string) => {
    console.log(`[handleDelete] Attempting to delete document: ${filename} (ID: ${id})`);
    
    if (!window.confirm(`Are you sure you want to delete "${filename}"? This will also remove all its chunks and embeddings.`)) {
      console.log(`[handleDelete] Deletion cancelled by user for: ${filename}`);
      return;
    }

    try {
      setDeletingId(id);
      setError(null);
      console.log(`[handleDelete] Calling deleteDocument API for ID: ${id}`);
      await deleteDocument(id);
      console.log(`[handleDelete] Successfully deleted document ID: ${id}`);
      setDocuments((prev) => prev.filter((d) => d.id !== id));
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to delete document.";
      console.error(`[handleDelete] Error deleting document ID ${id}:`, err);
      setError(msg);
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <section className="mx-auto mt-6 max-w-4xl">
      <div className="rounded-3xl bg-white p-6 shadow-soft">
        <p className="text-xs uppercase tracking-wide text-slate-500">
          Library
        </p>
        <h1 className="mt-1 text-2xl font-semibold text-slate-900">
          Your Documents
        </h1>
        <p className="mt-1 text-sm text-slate-600">
          Browse uploaded documents and start a chat session.
        </p>

        {loading && (
          <div className="mt-8">
            <Loader label="Loading documents..." />
          </div>
        )}

        {error && <p className="mt-6 text-sm text-rose-600">{error}</p>}

        {!loading && !error && documents.length === 0 && (
          <div className="mt-8 rounded-2xl border-2 border-dashed border-slate-200 p-8 text-center">
            <p className="text-sm text-slate-500">No documents yet.</p>
            <Link
              href="/"
              className="mt-3 inline-block rounded-xl bg-slate-900 px-5 py-2 text-sm font-medium text-white transition hover:bg-slate-700"
            >
              Upload your first PDF
            </Link>
          </div>
        )}

        {!loading && documents.length > 0 && (
          <div className="mt-6 space-y-3">
            {documents.map((doc) => (
              <div
                key={doc.id}
                className="flex items-center justify-between rounded-2xl border border-slate-200 bg-slate-50 px-5 py-4 transition hover:border-slate-300 hover:shadow-sm"
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-slate-900">
                    {doc.filename}
                  </p>
                  <p className="mt-0.5 text-xs text-slate-500">
                    {doc.chunk_count} chunks &middot;{" "}
                    {new Date(doc.created_at).toLocaleDateString("en-US", {
                      year: "numeric",
                      month: "short",
                      day: "numeric",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </p>
                </div>
                <div className="ml-4 flex shrink-0 items-center gap-2">
                  <Link
                    href={`/chat/doc/${doc.id}`}
                    className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-700"
                  >
                    Chat
                  </Link>
                  <button
                    onClick={() => handleDelete(doc.id, doc.filename)}
                    disabled={deletingId === doc.id}
                    className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-2 text-sm font-medium text-rose-600 transition hover:bg-rose-100 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {deletingId === doc.id ? "..." : "Delete"}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
