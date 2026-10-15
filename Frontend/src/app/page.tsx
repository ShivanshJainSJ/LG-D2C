"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ShieldCheck, FileText, ArrowRight, Zap, CheckCircle2, UserCheck, CreditCard } from "lucide-react";
import { getStoredSession } from "@/lib/api";

export default function Home() {
  const router = useRouter();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    const session = getStoredSession();
    if (session) {
      if (session.role === "ADMIN") {
        router.push("/admin/dashboard");
      } else {
        router.push("/agent/dashboard");
      }
    }
  }, [router]);

  if (!mounted) return null;

  return (
    <div className="min-h-screen bg-slate-900 text-white flex flex-col justify-between">
      {/* Navbar */}
      <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-lg bg-red-600 flex items-center justify-center font-black text-xl text-white shadow-lg shadow-red-600/30">
              LG
            </div>
            <div>
              <span className="font-extrabold text-xl tracking-tight text-white">Livguard</span>
              <span className="block text-[10px] font-semibold text-red-500 uppercase tracking-widest">
                D2C Quotations
              </span>
            </div>
          </div>
          <Link
            href="/login"
            className="px-5 py-2 rounded-lg bg-red-600 hover:bg-red-700 text-white text-sm font-semibold transition shadow-md shadow-red-600/20 flex items-center space-x-2"
          >
            <span>Sign In</span>
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </header>

      {/* Hero */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 flex-1 flex flex-col items-center text-center justify-center">
        <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-red-950/60 border border-red-800/50 text-red-400 text-xs font-semibold mb-6">
          <Zap className="w-3.5 h-3.5 fill-red-400" />
          <span>More Power. Less Waiting. Fast Charging. Long Lasting.</span>
        </div>

        <h1 className="text-4xl sm:text-6xl font-black tracking-tight max-w-4xl leading-tight">
          Enterprise <span className="text-red-500">Quotation & Order</span> Management System
        </h1>

        <p className="mt-6 text-lg text-slate-300 max-w-2xl leading-relaxed">
          Streamlined SKU quotation generation, server-verified pricing, controlled document revisions, and verified payment workflows for authorized Livguard agents and central administration.
        </p>

        {/* Brand Banner Card */}
        <div className="mt-10 w-full max-w-4xl rounded-2xl overflow-hidden border border-slate-700 shadow-2xl shadow-black/80 bg-slate-950">
          <img
            src="/assets/livguard_banner.jpeg"
            alt="Livguard Inverters & Lithium Battery Lineup"
            className="w-full h-auto object-cover max-h-72"
          />
        </div>

        {/* Action Buttons */}
        <div className="mt-10 flex flex-col sm:flex-row gap-4 w-full sm:w-auto">
          <Link
            href="/login"
            className="px-8 py-3.5 rounded-xl bg-red-600 hover:bg-red-700 text-white font-bold text-base shadow-xl shadow-red-600/30 flex items-center justify-center space-x-2 transition"
          >
            <UserCheck className="w-5 h-5" />
            <span>Agent Portal</span>
          </Link>
          <Link
            href="/login"
            className="px-8 py-3.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-white font-bold text-base border border-slate-700 flex items-center justify-center space-x-2 transition"
          >
            <ShieldCheck className="w-5 h-5" />
            <span>Admin Portal</span>
          </Link>
        </div>

        {/* Feature Highlights Grid */}
        <div className="mt-16 grid grid-cols-1 md:grid-cols-4 gap-6 text-left w-full">
          <div className="bg-slate-800/50 border border-slate-700/60 p-5 rounded-xl">
            <FileText className="w-6 h-6 text-red-500 mb-3" />
            <h3 className="font-bold text-white text-sm">SKU-Based Quotations</h3>
            <p className="text-xs text-slate-400 mt-1">
              Dynamic pricing, instant preview, coupon engine, and compliant GST calculations.
            </p>
          </div>
          <div className="bg-slate-800/50 border border-slate-700/60 p-5 rounded-xl">
            <CheckCircle2 className="w-6 h-6 text-green-500 mb-3" />
            <h3 className="font-bold text-white text-sm">Controlled Revisions</h3>
            <p className="text-xs text-slate-400 mt-1">
              Immutable snapshots for issued quotes, preserving complete historical version integrity.
            </p>
          </div>
          <div className="bg-slate-800/50 border border-slate-700/60 p-5 rounded-xl">
            <CreditCard className="w-6 h-6 text-blue-500 mb-3" />
            <h3 className="font-bold text-white text-sm">Two-Stage Verification</h3>
            <p className="text-xs text-slate-400 mt-1">
              Agents report full payment with reference; admin verifies before order confirmation.
            </p>
          </div>
          <div className="bg-slate-800/50 border border-slate-700/60 p-5 rounded-xl">
            <ShieldCheck className="w-6 h-6 text-purple-500 mb-3" />
            <h3 className="font-bold text-white text-sm">Branded Document Engine</h3>
            <p className="text-xs text-slate-400 mt-1">
              Pixel-perfect Livguard PDF and high-res PNG export powered by headless browser rendering.
            </p>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800 bg-slate-950 py-6 text-center text-xs text-slate-500">
        <p>&copy; {new Date().getFullYear()} Livguard Energy Technologies Pvt. Ltd. All rights reserved.</p>
        <p className="mt-1 text-slate-600">Enterprise D2C Quotation & Order Acceptance Platform</p>
      </footer>
    </div>
  );
}
