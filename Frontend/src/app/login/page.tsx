"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ShieldCheck, UserCheck, Lock, Mail, AlertCircle, Loader2, ArrowLeft } from "lucide-react";
import { api, setStoredSession } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const response = await api.post<{
        access_token: string;
        role: "ADMIN" | "AGENT";
        user_id: string;
        full_name: string;
        email: string;
      }>("/auth/login", { email, password });

      setStoredSession({
        token: response.access_token,
        role: response.role,
        userId: response.user_id,
        fullName: response.full_name,
        email: response.email,
      });

      if (response.role === "ADMIN") {
        router.push("/admin/dashboard");
      } else {
        router.push("/agent/dashboard");
      }
    } catch (err: any) {
      setError(err.message || "Failed to sign in. Please verify your credentials.");
    } finally {
      setLoading(false);
    }
  };

  const isProduction = process.env.NODE_ENV === "production";

  const fillCredentials = (role: "ADMIN" | "AGENT") => {
    if (isProduction) return;
    if (role === "ADMIN") {
      setEmail("admin@livguard.com");
      setPassword("Admin@123");
    } else {
      setEmail("agent@livguard.com");
      setPassword("Agent@123");
    }
    setError(null);
  };

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col justify-center py-12 sm:px-6 lg:px-8 relative">
      <div className="absolute top-6 left-6">
        <Link
          href="/"
          className="text-slate-400 hover:text-white flex items-center space-x-2 text-sm font-medium transition"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Home</span>
        </Link>
      </div>

      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <div className="w-16 h-16 rounded-2xl bg-black border border-slate-800 flex items-center justify-center mx-auto shadow-xl p-2">
          <img src="/assets/livguard_logo.jpg" alt="Livguard" className="w-full h-full object-contain" />
        </div>
        <h2 className="mt-4 text-3xl font-black text-white tracking-tight">Livguard Access Portal</h2>
        <p className="mt-2 text-sm text-slate-400">Sign in to manage quotations, products, and orders</p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md px-4">
        <div className="bg-slate-900 border border-slate-800 py-8 px-6 shadow-2xl rounded-2xl sm:px-10">
          {/* Demo account quick selector (development only - never rendered in production) */}
          {!isProduction && (
            <div className="mb-6">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 block mb-2 text-center">
                Quick Demo Fill (Development Only)
              </span>
              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => fillCredentials("ADMIN")}
                  className="py-2 px-3 border border-red-900/60 bg-red-950/40 hover:bg-red-900/60 rounded-lg text-xs font-bold text-red-300 flex items-center justify-center space-x-1.5 transition"
                >
                  <ShieldCheck className="w-4 h-4 text-red-500" />
                  <span>Admin Demo</span>
                </button>
                <button
                  type="button"
                  onClick={() => fillCredentials("AGENT")}
                  className="py-2 px-3 border border-slate-700 bg-slate-800 hover:bg-slate-700 rounded-lg text-xs font-bold text-slate-300 flex items-center justify-center space-x-1.5 transition"
                >
                  <UserCheck className="w-4 h-4 text-slate-400" />
                  <span>Agent Demo</span>
                </button>
              </div>
            </div>
          )}

          {error && (
            <div className="mb-6 p-3 rounded-lg bg-red-950/60 border border-red-800/60 flex items-start space-x-2.5 text-red-300 text-xs">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-red-400" />
              <span>{error}</span>
            </div>
          )}

          <form className="space-y-5" onSubmit={handleLogin}>
            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider">
                Email Address
              </label>
              <div className="mt-1 relative rounded-md shadow-sm">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                  <Mail className="w-4 h-4" />
                </div>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@livguard.com"
                  className="block w-full pl-10 pr-3 py-2.5 bg-slate-950 border border-slate-700 rounded-lg text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-red-500 transition"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider">
                Password
              </label>
              <div className="mt-1 relative rounded-md shadow-sm">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                  <Lock className="w-4 h-4" />
                </div>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="block w-full pl-10 pr-3 py-2.5 bg-slate-950 border border-slate-700 rounded-lg text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-red-500 transition"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 px-4 rounded-lg bg-red-600 hover:bg-red-700 text-white font-bold text-sm shadow-lg shadow-red-600/30 flex items-center justify-center space-x-2 transition disabled:opacity-50"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Signing In...</span>
                </>
              ) : (
                <span>Sign In</span>
              )}
            </button>
          </form>

          <div className="mt-6 text-center text-xs text-slate-500">
            Authorized Personnel Only &bull; Livguard Security Protocol
          </div>
        </div>
      </div>
    </div>
  );
}
