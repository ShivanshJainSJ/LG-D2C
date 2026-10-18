"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  FileText,
  Search,
  Filter,
  Download,
  CreditCard,
  Copy,
  Eye,
  Plus,
  Layers,
  FileDown,
  Image as ImageIcon,
  RotateCcw,
} from "lucide-react";
import { api } from "@/lib/api";
import { formatCurrency, formatDateTime } from "@/lib/utils";

interface AgentQuotation {
  id: string;
  quotation_number: string;
  current_revision_number: number;
  customer_name: string;
  customer_mobile: string;
  status: string;
  grand_total: number;
  revision_count: number;
  created_at: string;
}

export default function AgentQuotationsListPage() {
  const router = useRouter();
  const [quotations, setQuotations] = useState<AgentQuotation[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("");

  const fetchQuotations = async () => {
    try {
      setLoading(true);
      let url = "/agent/quotations";
      if (statusFilter) url += `?status_filter=${statusFilter}`;
      const data = await api.get<AgentQuotation[]>(url);
      setQuotations(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQuotations();
  }, [statusFilter]);

  const handleDuplicate = async (id: string) => {
    try {
      const res = await api.post<{ quotation_id: string }>(`/agent/quotations/${id}/duplicate`);
      alert("Quotation duplicated as a new draft!");
      fetchQuotations();
    } catch (err: any) {
      alert(err.message || "Failed to duplicate quotation");
    }
  };

  const handleReuse = async (id: string) => {
    try {
      const res = await api.post<{ new_quotation_id: string; message: string; price_updated_notice: string }>(
        `/agent/quotations/${id}/reuse`
      );
      alert(`${res.message}\n${res.price_updated_notice}`);
      router.push(`/agent/quotations/${res.new_quotation_id}`);
    } catch (err: any) {
      alert(err.message || "Failed to reuse quotation");
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "DRAFT":
        return <span className="px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 font-bold text-[10px]">Draft</span>;
      case "ISSUED":
        return <span className="px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 font-bold text-[10px]">Issued</span>;
      case "PAYMENT_PENDING":
        return <span className="px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 font-bold text-[10px]">Payment In Review</span>;
      case "PAYMENT_VERIFIED":
        return <span className="px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 font-bold text-[10px]">Payment Verified</span>;
      case "ORDER_CONFIRMED":
        return <span className="px-2 py-0.5 rounded-full bg-purple-50 text-purple-700 font-bold text-[10px]">Order Confirmed</span>;
      case "CANCELLED":
        return <span className="px-2 py-0.5 rounded-full bg-red-50 text-red-700 font-bold text-[10px]">Cancelled</span>;
      default:
        return <span>{status}</span>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight">My Quotations</h1>
          <p className="text-xs text-slate-500 mt-1">
            Track customer quotations, download official PDF/PNG documents and report payments
          </p>
        </div>
        <Link
          href="/agent/quotations/new"
          className="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-700 text-white text-xs font-bold flex items-center space-x-1.5 transition shadow-md shadow-red-600/20"
        >
          <Plus className="w-4 h-4" />
          <span>New Quotation</span>
        </Link>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center space-x-2 border-b border-slate-200 pb-3 overflow-x-auto">
        {[
          { label: "All My Quotes", value: "" },
          { label: "Issued", value: "ISSUED" },
          { label: "Drafts", value: "DRAFT" },
          { label: "Payment In Review", value: "PAYMENT_PENDING" },
          { label: "Confirmed Orders", value: "ORDER_CONFIRMED" },
        ].map((tab) => (
          <button
            key={tab.label}
            onClick={() => setStatusFilter(tab.value)}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition shrink-0 ${
              statusFilter === tab.value
                ? "bg-slate-900 text-white shadow-sm"
                : "bg-white border border-slate-200 text-slate-600 hover:bg-slate-50"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Quotations Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase tracking-wider text-[10px] font-bold">
              <tr>
                <th className="py-3 px-4">Quotation Number</th>
                <th className="py-3 px-4">Customer Name & Contact</th>
                <th className="py-3 px-4">Quotation Value</th>
                <th className="py-3 px-4">Version History</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-slate-400">
                    Loading your quotations...
                  </td>
                </tr>
              ) : quotations.length > 0 ? (
                quotations.map((q) => (
                  <tr key={q.id} className="hover:bg-slate-50/80 transition">
                    <td className="py-3.5 px-4 font-mono font-bold text-red-600 text-sm">
                      {q.quotation_number}
                    </td>
                    <td className="py-3.5 px-4">
                      <div className="font-bold text-slate-900">{q.customer_name}</div>
                      <div className="text-[10px] text-slate-400 font-medium">{q.customer_mobile}</div>
                    </td>
                    <td className="py-3.5 px-4 font-black text-slate-900 text-sm">
                      {formatCurrency(q.grand_total)}
                    </td>
                    <td className="py-3.5 px-4">
                      <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-bold text-[10px]">
                        <Layers className="w-3 h-3 text-slate-400" />
                        <span>Rev {q.current_revision_number} ({q.revision_count} ver)</span>
                      </span>
                    </td>
                    <td className="py-3.5 px-4">{getStatusBadge(q.status)}</td>
                    <td className="py-3.5 px-4 text-right">
                      <div className="inline-flex items-center space-x-1.5">
                        <Link
                          href={`/agent/quotations/${q.id}`}
                          className="px-2.5 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-800 font-bold transition flex items-center space-x-1"
                          title="View Details & Revisions"
                        >
                          <Eye className="w-3.5 h-3.5" />
                          <span>View</span>
                        </Link>
                        {q.status === "ISSUED" && (
                          <Link
                            href={`/agent/payments?quote_id=${q.id}`}
                            className="px-2.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-bold transition flex items-center space-x-1 shadow-sm"
                            title="Report Payment Received"
                          >
                            <CreditCard className="w-3.5 h-3.5" />
                            <span>Report Pay</span>
                          </Link>
                        )}
                        <button
                          onClick={() => handleReuse(q.id)}
                          className="px-2 py-1 rounded-lg bg-red-50 hover:bg-red-100 text-red-700 font-bold text-xs transition flex items-center space-x-1"
                          title="Reuse Quotation with Current Catalog Pricing"
                        >
                          <RotateCcw className="w-3.5 h-3.5" />
                          <span>Reuse</span>
                        </button>
                        <button
                          onClick={() => handleDuplicate(q.id)}
                          className="p-1.5 rounded-lg text-slate-400 hover:text-slate-800 hover:bg-slate-100 transition"
                          title="Duplicate as New Draft"
                        >
                          <Copy className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-slate-400">
                    No quotations found. Click "New Quotation" to generate your first quote.
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
