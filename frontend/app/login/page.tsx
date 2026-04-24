"use client";

import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { login, register } from "@/lib/api";
import { setToken } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    // Client-side validation
    if (username.trim().length < 3) {
      setError("Username must be at least 3 characters.");
      return;
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }

    setLoading(true);
    try {
      const result =
        mode === "login"
          ? await login({ username, password })
          : await register({ username, email, password });

      setToken(result.access_token);
      router.push("/");
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-[70vh] items-center justify-center">
      <div className="w-full max-w-md rounded-3xl bg-white p-8 shadow-soft">
        {/* Header */}
        <p className="text-sm font-medium text-slate-500">Document Intelligence</p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight text-slate-900">
          {mode === "login" ? "Welcome back" : "Create your account"}
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          {mode === "login"
            ? "Sign in to access your documents."
            : "Register to start uploading and querying PDFs."}
        </p>

        {/* Toggle */}
        <div className="mt-6 flex rounded-xl bg-slate-100 p-1">
          <button
            type="button"
            onClick={() => { setMode("login"); setError(null); }}
            className={`flex-1 rounded-lg py-2 text-sm font-medium transition ${
              mode === "login" ? "bg-white shadow-sm text-slate-900" : "text-slate-500 hover:text-slate-700"
            }`}
          >
            Sign In
          </button>
          <button
            type="button"
            onClick={() => { setMode("register"); setError(null); }}
            className={`flex-1 rounded-lg py-2 text-sm font-medium transition ${
              mode === "register" ? "bg-white shadow-sm text-slate-900" : "text-slate-500 hover:text-slate-700"
            }`}
          >
            Register
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700">Username</label>
            <input
              type="text"
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="mt-1 w-full rounded-xl border border-slate-200 px-4 py-2.5 text-sm text-slate-900 outline-none ring-0 transition focus:border-slate-400 focus:ring-2 focus:ring-slate-200"
              placeholder="yourname"
              autoComplete="username"
            />
          </div>

          {mode === "register" && (
            <div>
              <label className="block text-sm font-medium text-slate-700">Email</label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="mt-1 w-full rounded-xl border border-slate-200 px-4 py-2.5 text-sm text-slate-900 outline-none ring-0 transition focus:border-slate-400 focus:ring-2 focus:ring-slate-200"
                placeholder="you@example.com"
                autoComplete="email"
              />
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-slate-700">Password</label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 w-full rounded-xl border border-slate-200 px-4 py-2.5 text-sm text-slate-900 outline-none ring-0 transition focus:border-slate-400 focus:ring-2 focus:ring-slate-200"
              placeholder="••••••••"
              autoComplete={mode === "login" ? "current-password" : "new-password"}
            />
          </div>

          {error && (
            <p className="rounded-xl bg-rose-50 px-4 py-2.5 text-sm text-rose-600">{error}</p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="mt-2 w-full rounded-xl bg-slate-900 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:opacity-50"
          >
            {loading
              ? mode === "login" ? "Signing in…" : "Creating account…"
              : mode === "login" ? "Sign In" : "Create Account"}
          </button>
        </form>
      </div>
    </div>
  );
}
