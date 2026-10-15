"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  LayoutDashboard,
  FilePlus2,
  FileText,
  CreditCard,
  User,
  LogOut,
  Zap,
  Menu,
  X,
} from "lucide-react";
import { getStoredSession, clearStoredSession, UserSession } from "@/lib/api";

const agentNav = [
  { name: "Dashboard", href: "/agent/dashboard", icon: LayoutDashboard },
  { name: "New Quotation", href: "/agent/quotations/new", icon: FilePlus2 },
  { name: "My Quotations", href: "/agent/quotations", icon: FileText },
  { name: "Payments", href: "/agent/payments", icon: CreditCard },
  { name: "Profile", href: "/agent/profile", icon: User },
];

export default function AgentLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [session, setSession] = useState<UserSession | null>(null);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    const s = getStoredSession();
    if (!s || s.role !== "AGENT") {
      if (s?.role === "ADMIN") {
        router.push("/admin/dashboard");
      } else {
        router.push("/login");
      }
    } else {
      setSession(s);
    }
  }, [router]);

  const handleLogout = () => {
    clearStoredSession();
    router.push("/login");
  };

  if (!session) return null;

  return (
    <div className="min-h-screen bg-slate-100 flex flex-col">
      {/* Top Navbar */}
      <header className="h-16 bg-slate-950 border-b border-slate-800 text-white px-4 sm:px-6 flex items-center justify-between sticky top-0 z-40 shadow-md">
        <div className="flex items-center space-x-3">
          <Link href="/agent/dashboard" className="flex items-center space-x-2.5">
            <div className="w-9 h-9 rounded-lg bg-red-600 flex items-center justify-center font-black text-lg text-white shadow-md shadow-red-600/40">
              LG
            </div>
            <div>
              <span className="font-extrabold text-base text-white tracking-tight">Livguard</span>
              <span className="block text-[8px] font-bold text-red-500 uppercase tracking-widest">
                Agent Terminal
              </span>
            </div>
          </Link>
        </div>

        {/* Desktop Nav Links */}
        <nav className="hidden md:flex items-center space-x-1">
          {agentNav.map((item) => {
            const Icon = item.icon;
            const active = item.href === "/agent/quotations"
              ? pathname === "/agent/quotations"
              : pathname.startsWith(item.href);
            return (
              <Link
                key={item.name}
                href={item.href}
                className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition ${
                  active
                    ? "bg-red-600 text-white shadow-sm"
                    : "text-slate-300 hover:text-white hover:bg-slate-900"
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{item.name}</span>
              </Link>
            );
          })}
        </nav>

        {/* User Info & Mobile Toggle */}
        <div className="flex items-center space-x-3">
          <div className="hidden sm:flex items-center space-x-2 text-right">
            <div className="text-xs">
              <span className="font-bold text-white block">{session.fullName}</span>
              <span className="text-[10px] text-slate-400">Field Agent</span>
            </div>
          </div>
          <button
            onClick={handleLogout}
            title="Sign Out"
            className="hidden md:flex p-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-red-400 transition"
          >
            <LogOut className="w-4 h-4" />
          </button>
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="md:hidden p-2 rounded-lg text-slate-400 hover:bg-slate-900"
          >
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </header>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="md:hidden bg-slate-950 border-b border-slate-800 px-4 py-3 space-y-1">
          {agentNav.map((item) => {
            const Icon = item.icon;
            const active = pathname.startsWith(item.href);
            return (
              <Link
                key={item.name}
                href={item.href}
                onClick={() => setMobileMenuOpen(false)}
                className={`flex items-center space-x-2.5 px-3 py-2 rounded-lg text-xs font-bold transition ${
                  active ? "bg-red-600 text-white" : "text-slate-300 hover:bg-slate-900"
                }`}
              >
                <Icon className="w-4 h-4" />
                <span>{item.name}</span>
              </Link>
            );
          })}
          <button
            onClick={handleLogout}
            className="w-full flex items-center space-x-2.5 px-3 py-2 rounded-lg text-xs font-bold text-red-400 hover:bg-slate-900"
          >
            <LogOut className="w-4 h-4" />
            <span>Sign Out</span>
          </button>
        </div>
      )}

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8">{children}</main>
    </div>
  );
}
