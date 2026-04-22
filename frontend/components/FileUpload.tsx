"use client";

import { useCallback, useRef, useState } from "react";

interface FileUploadProps {
  onSelectFile: (file: File) => void;
  disabled?: boolean;
}

export default function FileUpload({ onSelectFile, disabled = false }: FileUploadProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const validateAndSend = useCallback(
    (file: File) => {
      if (!file.name.toLowerCase().endsWith(".pdf")) {
        setError("Only PDF files are allowed.");
        return;
      }
      setError(null);
      onSelectFile(file);
    },
    [onSelectFile],
  );

  return (
    <div className="space-y-3">
      <button
        type="button"
        disabled={disabled}
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          if (!disabled) setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setIsDragging(false);
          if (disabled) return;
          const file = e.dataTransfer.files?.[0];
          if (file) validateAndSend(file);
        }}
        className={`w-full rounded-2xl border-2 border-dashed bg-white p-10 text-center transition ${
          isDragging ? "border-slate-900 bg-slate-50" : "border-slate-300"
        } ${disabled ? "cursor-not-allowed opacity-60" : "cursor-pointer hover:border-slate-500"}`}
      >
        <p className="text-base font-medium text-slate-800">Drag & drop your PDF here</p>
        <p className="mt-2 text-sm text-slate-500">or click to browse files</p>
      </button>
      <input
        ref={inputRef}
        type="file"
        accept="application/pdf,.pdf"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) validateAndSend(file);
        }}
      />
      {error && <p className="text-sm text-rose-600">{error}</p>}
    </div>
  );
}
