"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  LayoutDashboard,
  FileText,
  CreditCard,
  ShoppingBag,
  Package,
  Tag,
  Ticket,
  Users,
  Settings,
  LogOut,
  ShieldCheck,
  Menu,
  X,
  Bell,
} from "lucide-react";
import { getStoredSession, clearStoredSession, UserSession } from "@/lib/api";

const navItems = [
  { name: "Dashboard", href: "/admin/dashboard", icon: LayoutDashboard },
  { name: "Quotations", href: "/admin/quotations", icon: FileText },
  { name: "Payments", href: "/admin/payments", icon: CreditCard },
  { name: "Orders", href: "/admin/orders", icon: ShoppingBag },
  { name: "Products", href: "/admin/products", icon: Package },
  { name: "Pricing", href: "/admin/pricing", icon: Tag },
  { name: "Coupons", href: "/admin/coupons", icon: Ticket },
  { name: "Agents", href: "/admin/agents", icon: Users },
  { name: "Settings", href: "/admin/settings", icon: Settings },
];

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [session, setSession] = useState<UserSession | null>(null);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    const s = getStoredSession();
    if (!s || s.role !== "ADMIN") {
      router.push("/login");
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
    <div className="min-h-screen bg-slate-100 flex">
      {/* Sidebar for Desktop */}
      <aside className="hidden lg:flex lg:flex-col lg:w-64 bg-slate-900 border-r border-slate-800 text-white">
        {/* Brand Header */}
        <div className="h-16 flex items-center px-6 border-b border-slate-800 space-x-3">
          <div className="w-9 h-9 rounded-lg bg-red-600 flex items-center justify-center font-black text-lg text-white shadow-md shadow-red-600/30">
            LG
          </div>
          <div>
            <span className="font-extrabold text-lg text-white tracking-tight">Livguard</span>
            <span className="block text-[9px] font-bold text-red-400 uppercase tracking-widest">
              Admin Portal
            </span>
          </div>
        </div>

        {/* Navigation Links */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = pathname.startsWith(item.href);
            return (
              <Link
                key={item.name}
                href={item.href}
                className={`flex items-center space-x-3 px-3.5 py-2.5 rounded-lg text-sm font-semibold transition ${
                  active
                    ? "bg-red-600 text-white shadow-md shadow-red-600/30"
                    : "text-slate-400 hover:text-white hover:bg-slate-800"
                }`}
              >
                <Icon className={`w-4 h-4 ${active ? "text-white" : "text-slate-400"}`} />
                <span>{item.name}</span>
              </Link>
            );
          })}
        </nav>

        {/* User Info & Logout */}
        <div className="p-4 border-t border-slate-800 bg-slate-950/60">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2.5 overflow-hidden">
              <div className="w-8 h-8 rounded-full bg-red-700/80 flex items-center justify-center text-xs font-bold text-white shrink-0">
                AD
              </div>
              <div className="overflow-hidden">
                <p className="text-xs font-bold text-white truncate">{session.fullName}</p>
                <p className="text-[10px] text-slate-400 truncate">{session.email}</p>
              </div>
            </div>
            <button
              onClick={handleLogout}
              title="Logout"
              className="p-1.5 rounded-md hover:bg-slate-800 text-slate-400 hover:text-red-400 transition"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Navbar */}
        <header className="h-16 bg-white border-b border-slate-200 px-4 sm:px-6 flex items-center justify-between sticky top-0 z-40 shadow-sm">
          <div className="flex items-center space-x-3">
            <button
              onClick={() => setMobileOpen(!mobileOpen)}
              className="lg:hidden p-2 rounded-lg text-slate-600 hover:bg-slate-100"
            >
              {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
            <span className="text-xs font-bold px-2.5 py-1 rounded bg-slate-100 text-slate-700 border border-slate-200 flex items-center space-x-1">
              <ShieldCheck className="w-3.5 h-3.5 text-red-600" />
              <span>Central Admin Session</span>
            </span>
          </div>

          <div className="flex items-center space-x-3">
            <div className="flex items-center space-x-2 text-xs font-medium text-slate-500">
              <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
              <span className="hidden sm:inline">System Live</span>
            </div>
          </div>
        </header>

        {/* Mobile menu dropdown */}
        {mobileOpen && (
          <div className="lg:hidden bg-slate-900 border-b border-slate-800 p-3 space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const active = pathname.startsWith(item.href);
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  onClick={() => setMobileOpen(false)}
                  className={`flex items-center space-x-3 px-3.5 py-2.5 rounded-lg text-sm font-semibold transition ${
                    active ? "bg-red-600 text-white" : "text-slate-400 hover:bg-slate-800"
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span>{item.name}</span>
                </Link>
              );
            })}
            <button
              onClick={handleLogout}
              className="w-full flex items-center space-x-3 px-3.5 py-2.5 rounded-lg text-sm font-semibold text-red-400 hover:bg-slate-800"
            >
              <LogOut className="w-4 h-4" />
              <span>Logout</span>
            </button>
          </div>
        )}

        {/* Page Content */}
        <main className="flex-1 p-4 sm:p-6 lg:p-8 overflow-y-auto">{children}</main>
      </div>
    </div>
  );
}
