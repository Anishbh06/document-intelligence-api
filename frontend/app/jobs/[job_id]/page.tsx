"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import Loader from "@/components/Loader";
import ProgressBar from "@/components/ProgressBar";
import StatusBadge from "@/components/StatusBadge";
import { getJob } from "@/lib/api";
import { JobResponse } from "@/lib/types";

export default function JobPage() {
  const params = useParams();
  const router = useRouter();
  const jobId = params.job_id as string;

  const [job, setJob] = useState<JobResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let interval: NodeJS.Timeout | null = null;
    let mounted = true;

    const fetchJob = async () => {
      try {
        const current = await getJob(jobId);
        if (!mounted) return;
        setJob(current);
        setError(null);

        if (current.status === "completed") {
          router.replace(`/chat/${jobId}`);
        }
      } catch (err) {
        if (!mounted) return;
        setError(err instanceof Error ? err.message : "Could not load job.");
      }
    };

    void fetchJob();
    interval = setInterval(() => {
      void fetchJob();
    }, 2000);

    return () => {
      mounted = false;
      if (interval) clearInterval(interval);
    };
  }, [jobId, router]);

  const progressValue = useMemo(() => {
    if (!job) return 0;
    if (job.total_chunks > 0) {
      return Math.round((job.processed_chunks / job.total_chunks) * 100);
    }
    return job.progress;
  }, [job]);

  return (
    <section className="mx-auto mt-10 max-w-2xl rounded-3xl bg-white p-8 shadow-soft">
      <p className="text-sm font-medium text-slate-500">Processing</p>
      <h1 className="mt-2 text-2xl font-semibold text-slate-900">
        Job #{jobId}
      </h1>

      {!job && !error && <div className="mt-6"><Loader label="Fetching job status..." /></div>}
      {error && <p className="mt-6 text-sm text-rose-600">{error}</p>}

      {job && (
        <div className="mt-6 space-y-5">
          <div className="flex items-center justify-between rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
            <p className="text-sm text-slate-600">File: {job.filename}</p>
            <StatusBadge status={job.status} />
          </div>

          <ProgressBar value={progressValue} />

          <p className="text-sm text-slate-600">
            Chunks processed: {job.processed_chunks} / {job.total_chunks || "-"}
          </p>

          {job.status === "failed" && (
            <p className="rounded-xl bg-rose-50 p-3 text-sm text-rose-700">
              {job.error_message || "Processing failed. Please retry upload."}
            </p>
          )}
        </div>
      )}
    </section>
  );
}

