"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  FilePlus2,
  FileText,
  Clock,
  CheckCircle,
  ShoppingBag,
  TrendingUp,
  ArrowRight,
  Zap,
} from "lucide-react";
import { api } from "@/lib/api";
import { formatCurrency, formatDateTime } from "@/lib/utils";

interface AgentStats {
  total_quotations: number;
  draft_quotations: number;
  issued_quotations: number;
  payment_pending: number;
  payment_verified: number;
  confirmed_orders: number;
  total_quoted_value: number;
  conversion_rate: number;
  recent_quotations: {
    id: string;
    quotation_number: string;
    customer_name: string;
    status: string;
    grand_total: number;
    created_at: string;
  }[];
}

export default function AgentDashboardPage() {
  const [stats, setStats] = useState<AgentStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        setLoading(true);
        const data = await api.get<AgentStats>("/agent/dashboard/stats");
        setStats(data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchStats();
  }, []);

  return (
    <div className="space-y-6">
      {/* Welcome & New Quote Action */}
      <div className="bg-slate-900 rounded-2xl p-6 sm:p-8 text-white relative overflow-hidden shadow-xl border border-slate-800">
        <div className="relative z-10 max-w-xl">
          <div className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-red-950/80 border border-red-800/60 text-red-400 text-[10px] font-bold uppercase tracking-wider mb-3">
            <Zap className="w-3 h-3 fill-red-400" />
            <span>Livguard Field Agent Terminal</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-black tracking-tight">
            Create & Manage <span className="text-red-500">Instant Quotations</span>
          </h1>
          <p className="text-xs text-slate-300 mt-2 leading-relaxed">
            Generate SKU-based branded quotations with authoritative pricing, coupon discounts, statutory GST, and real-time revisions.
          </p>
          <div className="mt-5">
            <Link
              href="/agent/quotations/new"
              className="inline-flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-red-600 hover:bg-red-700 text-white font-bold text-xs shadow-lg shadow-red-600/40 transition"
            >
              <FilePlus2 className="w-4 h-4" />
              <span>Create New Quotation</span>
            </Link>
          </div>
        </div>

        {/* Brand visual banner preview in background */}
        <div className="absolute right-0 top-0 bottom-0 w-1/3 opacity-20 hidden md:block">
          <img
            src="/assets/livguard_banner.jpeg"
            alt="Livguard Inverters"
            className="w-full h-full object-cover"
          />
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {/* Total Quotes */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
            My Quotations
          </span>
          <p className="text-2xl font-black text-slate-900 mt-1">{stats?.total_quotations ?? 0}</p>
          <span className="text-[10px] text-slate-500 mt-1 block">
            {stats?.issued_quotations ?? 0} issued &bull; {stats?.draft_quotations ?? 0} drafts
          </span>
        </div>

        {/* Under Review */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
            Payment In Review
          </span>
          <p className="text-2xl font-black text-amber-600 mt-1">{stats?.payment_pending ?? 0}</p>
          <span className="text-[10px] text-slate-500 mt-1 block">Awaiting admin verification</span>
        </div>

        {/* Confirmed Orders */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
            Confirmed Orders
          </span>
          <p className="text-2xl font-black text-emerald-600 mt-1">{stats?.confirmed_orders ?? 0}</p>
          <span className="text-[10px] text-slate-500 mt-1 block">
            Conversion: <strong className="text-slate-800">{stats?.conversion_rate ?? 0}%</strong>
          </span>
        </div>

        {/* Pipeline Value */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
            Total Quoted Value
          </span>
          <p className="text-lg font-black text-slate-900 mt-1">
            {formatCurrency(stats?.total_quoted_value)}
          </p>
          <span className="text-[10px] text-slate-500 mt-1 block">Active pipeline estimate</span>
        </div>
      </div>

      {/* Recent Quotations Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-4 sm:p-5 border-b border-slate-200 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-slate-900">Recent Quotations</h3>
            <p className="text-xs text-slate-400 mt-0.5">Your latest customer quotations</p>
          </div>
          <Link
            href="/agent/quotations"
            className="text-xs font-bold text-red-600 hover:text-red-700 flex items-center space-x-1"
          >
            <span>View All</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase tracking-wider text-[10px] font-bold">
              <tr>
                <th className="py-3 px-4">Quotation Number</th>
                <th className="py-3 px-4">Customer Name</th>
                <th className="py-3 px-4">Amount</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Created Date</th>
                <th className="py-3 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-slate-400">
                    Loading activity...
                  </td>
                </tr>
              ) : stats?.recent_quotations && stats.recent_quotations.length > 0 ? (
                stats.recent_quotations.map((q) => (
                  <tr key={q.id} className="hover:bg-slate-50/80 transition">
                    <td className="py-3.5 px-4 font-mono font-bold text-red-600">
                      {q.quotation_number || "DRAFT"}
                    </td>
                    <td className="py-3.5 px-4 font-bold text-slate-900">{q.customer_name}</td>
                    <td className="py-3.5 px-4 font-black text-slate-900">{formatCurrency(q.grand_total)}</td>
                    <td className="py-3.5 px-4">
                      <span className="px-2 py-0.5 rounded-full bg-slate-100 font-bold text-[10px] text-slate-700">
                        {q.status}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-slate-400">{formatDateTime(q.created_at)}</td>
                    <td className="py-3.5 px-4 text-right">
                      <Link
                        href={`/agent/quotations/${q.id}`}
                        className="px-2.5 py-1 rounded bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold transition inline-flex items-center space-x-1"
                      >
                        <span>View</span>
                        <ArrowRight className="w-3 h-3" />
                      </Link>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-slate-400">
                    No quotations generated yet. Click "Create New Quotation" to get started!
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
