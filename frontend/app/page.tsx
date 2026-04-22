"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import FileUpload from "@/components/FileUpload";
import Loader from "@/components/Loader";
import { uploadPdf } from "@/lib/api";

export default function UploadPage() {
  const router = useRouter();
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [jobId, setJobId] = useState<number | null>(null);

  const handleUpload = async (file: File) => {
    try {
      setError(null);
      setIsUploading(true);
      const response = await uploadPdf(file);
      setJobId(response.job.id);
      router.push(`/jobs/${response.job.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <section className="mx-auto mt-10 max-w-2xl rounded-3xl bg-white p-8 shadow-soft">
      <p className="text-sm font-medium text-slate-500">Document Intelligence</p>
      <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-900">
        Upload your PDF
      </h1>
      <p className="mt-2 text-sm text-slate-600">
        Drop a document to start background processing and semantic indexing.
      </p>

      <div className="mt-8">
        <FileUpload onSelectFile={handleUpload} disabled={isUploading} />
      </div>

      <div className="mt-4 min-h-6">
        {isUploading && <Loader label="Uploading and creating job..." />}
        {!isUploading && jobId && (
          <p className="text-sm text-slate-600">
            Job created: <span className="font-semibold">#{jobId}</span>
          </p>
        )}
        {error && <p className="text-sm text-rose-600">{error}</p>}
      </div>
    </section>
  );
}
