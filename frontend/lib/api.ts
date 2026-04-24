import {
  DocumentListResponse,
  JobResponse,
  LoginPayload,
  QueryResponse,
  RegisterPayload,
  TokenResponse,
  UploadJobResponse,
} from "@/lib/types";
import { clearAuth, getToken } from "@/lib/auth";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";


// ── Core fetch wrapper ────────────────────────────────────────────────────────

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken();

  const response = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });

  if (response.status === 401) {
    // Only force-logout if the user WAS authenticated (token expired).
    // If there's no token, this is a login failure — fall through to normal
    // error handling so the UI can display "Invalid username or password".
    if (getToken()) {
      clearAuth();
      if (typeof window !== "undefined") {
        window.location.href = "/login";
      }
      throw new Error("Session expired. Please sign in again.");
    }
  }

  if (!response.ok) {
    let errorMessage = `Request failed (${response.status})`;
    try {
      const data = await response.json() as {
        error?: { message?: string };
        detail?: Array<{ msg: string; loc?: string[] }> | string;
      };
      if (data.error?.message) {
        // Our standard APIError / RequestValidationError format
        errorMessage = data.error.message;
      } else if (Array.isArray(data.detail)) {
        // Raw Pydantic 422 fallback
        errorMessage = data.detail
          .map((e) => e.msg?.replace("Value error, ", "") ?? "Validation error")
          .join("; ");
      } else if (typeof data.detail === "string") {
        errorMessage = data.detail;
      }
    } catch {
      errorMessage = response.statusText || errorMessage;
    }
    throw new Error(errorMessage);
  }

  return (await response.json()) as T;
}

// ── Auth endpoints ────────────────────────────────────────────────────────────

export async function login(payload: LoginPayload): Promise<TokenResponse> {
  return request<TokenResponse>("/api/v1/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function register(payload: RegisterPayload): Promise<TokenResponse> {
  return request<TokenResponse>("/api/v1/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

// ── Document endpoints ────────────────────────────────────────────────────────

export async function uploadPdf(file: File): Promise<UploadJobResponse> {
  const formData = new FormData();
  formData.append("file", file);
  return request<UploadJobResponse>("/api/v1/upload", { method: "POST", body: formData });
}

export async function getJob(jobId: string): Promise<JobResponse> {
  return request<JobResponse>(`/api/v1/jobs/${jobId}`);
}

export async function getDocuments(): Promise<DocumentListResponse> {
  return request<DocumentListResponse>("/api/v1/documents");
}

export async function deleteDocument(documentId: number): Promise<{ message: string }> {
  return request<{ message: string }>(`/api/v1/documents/${documentId}`, { method: "DELETE" });
}

export async function queryDocument(documentId: number, question: string): Promise<QueryResponse> {
  return request<QueryResponse>("/api/v1/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ document_id: documentId, question }),
  });
}
