"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";

export default function LoginPage() {
  const { login, firebaseUser, loading, error, clearError } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // Redirect if already signed in
  if (!loading && firebaseUser) {
    router.replace("/dashboard");
    return null;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    clearError();
    setSubmitting(true);
    try {
      await login(email.trim(), password);
      router.push("/dashboard");
    } catch {
      // error is set via context
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-md rounded-2xl border-2 border-aqua bg-white p-8 shadow-lg">
        {/* ── Header ──────────────────────────────────────────────── */}
        <h1 className="mb-1 text-center text-2xl font-bold text-dark-blue">
          💧 AquaSmart
        </h1>
        <p className="mb-6 text-center text-sm text-steel">
          Sign in with your kiosk email and password
        </p>

        {/* ── Error banner ────────────────────────────────────────── */}
        {error && (
          <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-danger">
            {error}
          </div>
        )}

        {/* ── Form ────────────────────────────────────────────────── */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label
              htmlFor="email"
              className="mb-1 block text-sm font-medium text-app-bg"
            >
              Email
            </label>
            <input
              id="email"
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="your@gmail.com"
              className="w-full rounded-lg border border-gray-300 px-4 py-3 text-sm outline-none transition focus:border-aqua focus:ring-2 focus:ring-aqua/30"
            />
          </div>

          <div>
            <label
              htmlFor="password"
              className="mb-1 block text-sm font-medium text-app-bg"
            >
              Password
            </label>
            <input
              id="password"
              type="password"
              required
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full rounded-lg border border-gray-300 px-4 py-3 text-sm outline-none transition focus:border-aqua focus:ring-2 focus:ring-aqua/30"
            />
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-lg bg-dark-blue py-3 text-sm font-bold text-white transition hover:bg-dark-blue/90 disabled:opacity-50"
          >
            {submitting ? "Signing in…" : "Login"}
          </button>
        </form>

        {/* ── Footer link ─────────────────────────────────────────── */}
        <p className="mt-5 text-center text-sm text-steel">
          No account?{" "}
          <span className="font-semibold text-dark-blue">
            Register at the AquaSmart kiosk.
          </span>
        </p>
      </div>
    </main>
  );
}
