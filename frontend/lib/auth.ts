/**
 * auth.ts — thin client-side auth layer.
 *
 * Token is stored in localStorage under "doc_intel_token".
 * All helpers are plain functions (no React dependency) so they can be
 * used both in components and in api.ts.
 */

const TOKEN_KEY = "doc_intel_token";
const USER_KEY  = "doc_intel_user";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearAuth(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export function isAuthenticated(): boolean {
  return Boolean(getToken());
}
