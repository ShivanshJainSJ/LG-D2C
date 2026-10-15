"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  FileText,
  CreditCard,
  ShoppingBag,
  TrendingUp,
  Clock,
  CheckCircle,
  Users,
  Ticket,
  AlertTriangle,
  ArrowRight,
  RefreshCw,
} from "lucide-react";
import { api } from "@/lib/api";
import { formatCurrency } from "@/lib/utils";

interface DashboardMetrics {
  total_quotations: number;
  quotations_today: number;
  quotations_this_month: number;
  total_quoted_value: number;
  pending_payments_count: number;
  verified_payments_count: number;
  orders_received_count: number;
  total_verified_revenue: number;
  active_agents: number;
  inactive_agents: number;
  total_coupons_used: number;
}

interface ChartData {
  timeline: { date: string; count: number }[];
  agents: {
    agent_name: string;
    quotation_count: number;
    quoted_value: number;
    orders_confirmed: number;
    conversion_rate: number;
  }[];
  top_products: { name: string; quantity: number }[];
}

export default function AdminDashboardPage() {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [charts, setCharts] = useState<ChartData | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [m, c] = await Promise.all([
        api.get<DashboardMetrics>("/admin/dashboard/metrics"),
        api.get<ChartData>("/admin/dashboard/charts"),
      ]);
      setMetrics(m);
      setCharts(c);
    } catch (err) {
      console.error("Dashboard fetch error:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  return (
    <div className="space-y-6">
      {/* Title & Refresh */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight">Executive Dashboard</h1>
          <p className="text-xs text-slate-500 mt-1">
            Real-time quotation metrics, payment review queues, and conversion tracking
          </p>
        </div>
        <button
          onClick={fetchData}
          disabled={loading}
          className="inline-flex items-center space-x-2 px-3 py-2 rounded-lg bg-white border border-slate-200 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition shadow-sm"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin text-red-600" : ""}`} />
          <span>Refresh Data</span>
        </button>
      </div>

      {/* Review Queue Urgent Banner */}
      {metrics && metrics.pending_payments_count > 0 && (
        <div className="bg-amber-50 border-l-4 border-amber-500 p-4 rounded-r-xl shadow-sm flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0" />
            <div>
              <h4 className="text-sm font-bold text-amber-900">
                {metrics.pending_payments_count} Payment Report{metrics.pending_payments_count > 1 ? "s" : ""} Awaiting Review
              </h4>
              <p className="text-xs text-amber-700 mt-0.5">
                Agents have reported customer transactions. Review transaction proofs to verify and confirm orders.
              </p>
            </div>
          </div>
          <Link
            href="/admin/payments"
            className="px-3.5 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-700 text-white text-xs font-bold transition flex items-center space-x-1.5 shrink-0 shadow-sm"
          >
            <span>Review Queue</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      )}

      {/* Primary KPI Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Quotes */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-bold uppercase tracking-wider">Total Quotations</span>
            <div className="p-2 rounded-lg bg-red-50 text-red-600">
              <FileText className="w-4 h-4" />
            </div>
          </div>
          <p className="text-2xl font-black text-slate-900 mt-2">{metrics?.total_quotations ?? 0}</p>
          <div className="mt-2 flex items-center space-x-3 text-xs text-slate-500">
            <span>Today: <strong className="text-slate-800">{metrics?.quotations_today ?? 0}</strong></span>
            <span>&bull;</span>
            <span>This Month: <strong className="text-slate-800">{metrics?.quotations_this_month ?? 0}</strong></span>
          </div>
        </div>

        {/* Quoted Value */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-bold uppercase tracking-wider">Total Quoted Value</span>
            <div className="p-2 rounded-lg bg-slate-100 text-slate-700">
              <TrendingUp className="w-4 h-4" />
            </div>
          </div>
          <p className="text-2xl font-black text-slate-900 mt-2">
            {formatCurrency(metrics?.total_quoted_value)}
          </p>
          <p className="mt-2 text-[11px] text-slate-400">
            Pipeline estimate (uncollected quotations)
          </p>
        </div>

        {/* Verified Revenue */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-bold uppercase tracking-wider">Verified Revenue</span>
            <div className="p-2 rounded-lg bg-emerald-50 text-emerald-600">
              <CheckCircle className="w-4 h-4" />
            </div>
          </div>
          <p className="text-2xl font-black text-emerald-600 mt-2">
            {formatCurrency(metrics?.total_verified_revenue)}
          </p>
          <p className="mt-2 text-xs text-slate-500">
            {metrics?.verified_payments_count ?? 0} verified transactions
          </p>
        </div>

        {/* Confirmed Orders */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-xs font-bold uppercase tracking-wider">Confirmed Orders</span>
            <div className="p-2 rounded-lg bg-blue-50 text-blue-600">
              <ShoppingBag className="w-4 h-4" />
            </div>
          </div>
          <p className="text-2xl font-black text-slate-900 mt-2">{metrics?.orders_received_count ?? 0}</p>
          <div className="mt-2 flex items-center space-x-2 text-xs text-slate-500">
            <span>Active Agents: <strong className="text-slate-800">{metrics?.active_agents ?? 0}</strong></span>
          </div>
        </div>
      </div>

      {/* Charts & Analytics Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Quotation Timeline Chart (CSS-based bar visualization) */}
        <div className="lg:col-span-2 bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
          <h3 className="text-sm font-bold text-slate-900">Quotation Activity (Last 7 Days)</h3>
          <p className="text-xs text-slate-400 mt-0.5">Volume of quotations generated per day</p>

          <div className="mt-6 flex items-end justify-between h-48 pt-6 border-b border-slate-100">
            {charts?.timeline.map((item) => {
              const maxCount = Math.max(...charts.timeline.map((t) => t.count), 5);
              const heightPercent = Math.round((item.count / maxCount) * 100);
              return (
                <div key={item.date} className="flex-1 flex flex-col items-center gap-2 group">
                  <span className="text-[10px] font-bold text-slate-600 group-hover:text-red-600 transition">
                    {item.count}
                  </span>
                  <div
                    style={{ height: `${Math.max(heightPercent, 8)}%` }}
                    className="w-8 sm:w-12 bg-red-500/80 hover:bg-red-600 rounded-t-md transition-all shadow-sm"
                  />
                  <span className="text-[10px] text-slate-400 font-medium">
                    {new Date(item.date).toLocaleDateString("en-IN", { weekday: "short" })}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Top Products */}
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col">
          <h3 className="text-sm font-bold text-slate-900">Top Quoted Products</h3>
          <p className="text-xs text-slate-400 mt-0.5">Ranked by total units in quotations</p>

          <div className="mt-6 space-y-4 flex-1">
            {charts?.top_products && charts.top_products.length > 0 ? (
              charts.top_products.map((p, idx) => (
                <div key={p.name} className="flex items-center justify-between text-xs">
                  <div className="flex items-center space-x-2.5 overflow-hidden pr-2">
                    <span className="w-5 h-5 rounded-full bg-slate-100 font-bold text-slate-600 flex items-center justify-center shrink-0">
                      {idx + 1}
                    </span>
                    <span className="font-semibold text-slate-800 truncate">{p.name}</span>
                  </div>
                  <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-bold shrink-0">
                    {p.quantity} units
                  </span>
                </div>
              ))
            ) : (
              <p className="text-xs text-slate-400 text-center my-auto">No products quoted yet</p>
            )}
          </div>
        </div>
      </div>

      {/* Agent Performance Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-5 border-b border-slate-200">
          <h3 className="text-sm font-bold text-slate-900">Agent Performance & Conversion</h3>
          <p className="text-xs text-slate-400 mt-0.5">Quotations generated versus verified order conversions</p>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase tracking-wider text-[10px] font-bold">
              <tr>
                <th className="py-3 px-4">Agent Name</th>
                <th className="py-3 px-4">Quotations</th>
                <th className="py-3 px-4">Total Quoted Value</th>
                <th className="py-3 px-4">Orders Confirmed</th>
                <th className="py-3 px-4">Conversion Rate</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {charts?.agents && charts.agents.length > 0 ? (
                charts.agents.map((ag) => (
                  <tr key={ag.agent_name} className="hover:bg-slate-50/80 transition">
                    <td className="py-3 px-4 font-bold text-slate-900">{ag.agent_name}</td>
                    <td className="py-3 px-4 text-slate-600 font-semibold">{ag.quotation_count}</td>
                    <td className="py-3 px-4 text-slate-900 font-bold">{formatCurrency(ag.quoted_value)}</td>
                    <td className="py-3 px-4 text-emerald-600 font-bold">{ag.orders_confirmed}</td>
                    <td className="py-3 px-4">
                      <div className="flex items-center space-x-2">
                        <div className="w-16 bg-slate-100 rounded-full h-1.5 overflow-hidden">
                          <div
                            className="bg-emerald-500 h-1.5 rounded-full"
                            style={{ width: `${Math.min(ag.conversion_rate, 100)}%` }}
                          />
                        </div>
                        <span className="font-bold text-slate-700">{ag.conversion_rate}%</span>
                      </div>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={5} className="py-6 text-center text-slate-400">
                    No agent activity recorded yet.
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
