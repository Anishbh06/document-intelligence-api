export type JobStatus = "pending" | "processing" | "completed" | "failed";

export interface JobResponse {
  id: number;
  status: JobStatus;
  progress: number;
  total_chunks: number;
  processed_chunks: number;
  filename: string;
  document_id: number | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface UploadJobResponse {
  message: string;
  job: JobResponse;
}

export interface Citation {
  id: number;
  chunk_index: number;
  content: string;
}

export interface QueryResponse {
  answer: string;
  citations?: Citation[];
}

export interface DocumentResponse {
  id: number;
  filename: string;
  created_at: string;
  chunk_count: number;
}

export interface DocumentListResponse {
  documents: DocumentResponse[];
  total: number;
}

// ── Auth types ────────────────────────────────────────────────────────────────

export interface UserResponse {
  id: number;
  username: string;
  email: string;
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: UserResponse;
}

export interface LoginPayload {
  username: string;
  password: string;
}

export interface RegisterPayload {
  username: string;
  email: string;
  password: string;
}

