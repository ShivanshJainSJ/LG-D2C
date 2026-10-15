"use client";

import { useEffect, useState } from "react";
import {
  FileText,
  Search,
  Filter,
  Download,
  Eye,
  XCircle,
  CheckCircle2,
  Clock,
  Layers,
  FileDown,
  Image as ImageIcon,
  X,
  AlertCircle,
} from "lucide-react";
import { api } from "@/lib/api";
import { formatCurrency, formatDateTime } from "@/lib/utils";

interface QuotationListItem {
  id: string;
  quotation_number: string | null;
  current_revision_number: number;
  customer_name: string;
  customer_mobile: string;
  customer_email: string | null;
  agent_id: string;
  agent_name: string;
  status: string;
  grand_total: number;
  revision_count: number;
  created_at: string;
}

interface QuotationDetails {
  id: string;
  quotation_number: string;
  customer_name: string;
  customer_mobile: string;
  customer_email: string | null;
  customer_address: string | null;
  agent_name: string;
  status: string;
  cancellation_reason: string | null;
  created_at: string;
  revisions: {
    id: string;
    revision_number: number;
    revision_label: string;
    subtotal: number;
    discount_amount: number;
    coupon_code: string | null;
    tax_rate: number;
    tax_amount: number;
    grand_total: number;
    is_superseded: boolean;
    created_at: string;
    items: {
      id: string;
      sku: string;
      product_name: string;
      description: string | null;
      image_url?: string | null;
      unit_price: number;
      quantity: number;
      total_price: number;
    }[];
  }[];
}

export default function AdminQuotationsPage() {
  const [quotations, setQuotations] = useState<QuotationListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  // Details Modal
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [activeDetails, setActiveDetails] = useState<QuotationDetails | null>(null);
  const [selectedRevIndex, setSelectedRevIndex] = useState(0);
  const [detailsLoading, setDetailsLoading] = useState(false);

  // Cancel Modal
  const [cancelOpen, setCancelOpen] = useState(false);
  const [selectedQuoteId, setSelectedQuoteId] = useState<string | null>(null);
  const [cancelReason, setCancelReason] = useState("");
  const [cancelLoading, setCancelLoading] = useState(false);

  const fetchQuotations = async () => {
    try {
      setLoading(true);
      let url = "/admin/quotations?";
      if (search) url += `search=${encodeURIComponent(search)}&`;
      if (statusFilter) url += `status_filter=${encodeURIComponent(statusFilter)}&`;

      const data = await api.get<{ total: number; items: QuotationListItem[] }>(url);
      setQuotations(data.items);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQuotations();
  }, [statusFilter]);

  const viewDetails = async (id: string) => {
    setDetailsOpen(true);
    setDetailsLoading(true);
    setSelectedRevIndex(0);
    try {
      const data = await api.get<QuotationDetails>(`/admin/quotations/${id}`);
      setActiveDetails(data);
    } catch (err) {
      console.error(err);
    } finally {
      setDetailsLoading(false);
    }
  };

  const handleCancelSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedQuoteId || !cancelReason.trim()) return;
    setCancelLoading(true);

    try {
      await api.post(`/admin/quotations/${selectedQuoteId}/cancel`, {
        reason: cancelReason.trim(),
      });
      setCancelOpen(false);
      setCancelReason("");
      fetchQuotations();
      if (detailsOpen && activeDetails?.id === selectedQuoteId) {
        viewDetails(selectedQuoteId);
      }
    } catch (err: any) {
      alert(err.message || "Failed to cancel quotation");
    } finally {
      setCancelLoading(false);
    }
  };

  const downloadDoc = async (quoteId: string, revId: string, format: "pdf" | "png") => {
    try {
      const blob = await api.get<Blob>(`/admin/quotations/${quoteId}/revisions/${revId}/${format}`);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `Livguard_Quotation_${format.toUpperCase()}.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err: any) {
      alert("Failed to download document: " + err.message);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "DRAFT":
        return <span className="px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 font-bold text-[10px]">Draft</span>;
      case "ISSUED":
        return <span className="px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 font-bold text-[10px]">Issued</span>;
      case "PAYMENT_PENDING":
        return <span className="px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 font-bold text-[10px]">Payment Review</span>;
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
      <div>
        <h1 className="text-2xl font-black text-slate-900 tracking-tight">Central Quotations Master</h1>
        <p className="text-xs text-slate-500 mt-1">
          Monitor all issued quotations, audit immutable revisions, review pricing calculations and export PDF/PNG documents
        </p>
      </div>

      {/* Filter Toolbar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row items-center gap-3">
        <div className="relative flex-1 w-full">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
          <input
            type="text"
            placeholder="Search by quotation number, customer name, or mobile..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && fetchQuotations()}
            className="w-full pl-9 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-red-500 focus:bg-white transition"
          />
        </div>

        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs font-semibold text-slate-700 focus:outline-none focus:ring-2 focus:ring-red-500 w-full md:w-auto"
        >
          <option value="">All Statuses</option>
          <option value="DRAFT">Draft</option>
          <option value="ISSUED">Issued</option>
          <option value="PAYMENT_PENDING">Payment Pending</option>
          <option value="PAYMENT_VERIFIED">Payment Verified</option>
          <option value="ORDER_CONFIRMED">Order Confirmed</option>
          <option value="CANCELLED">Cancelled</option>
        </select>

        <button
          onClick={fetchQuotations}
          className="px-4 py-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-xs font-semibold text-slate-700 transition shrink-0"
        >
          Apply Filters
        </button>
      </div>

      {/* Quotations Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase tracking-wider text-[10px] font-bold">
              <tr>
                <th className="py-3 px-4">Quotation Number</th>
                <th className="py-3 px-4">Customer Details</th>
                <th className="py-3 px-4">Prepared By Agent</th>
                <th className="py-3 px-4">Grand Total</th>
                <th className="py-3 px-4">Revisions</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-400">
                    Loading quotation records...
                  </td>
                </tr>
              ) : quotations.length > 0 ? (
                quotations.map((q) => (
                  <tr key={q.id} className="hover:bg-slate-50/80 transition">
                    <td className="py-3.5 px-4 font-mono font-black text-red-600">
                      {q.quotation_number || "DRAFT (UNISSUED)"}
                    </td>
                    <td className="py-3.5 px-4">
                      <div className="font-bold text-slate-900">{q.customer_name}</div>
                      <div className="text-[10px] text-slate-400 font-medium">{q.customer_mobile}</div>
                    </td>
                    <td className="py-3.5 px-4 font-semibold text-slate-700">{q.agent_name}</td>
                    <td className="py-3.5 px-4 font-black text-slate-900 text-sm">
                      {formatCurrency(q.grand_total)}
                    </td>
                    <td className="py-3.5 px-4">
                      <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-bold text-[10px]">
                        <Layers className="w-3 h-3 text-slate-400" />
                        <span>{q.revision_count} ver</span>
                      </span>
                    </td>
                    <td className="py-3.5 px-4">{getStatusBadge(q.status)}</td>
                    <td className="py-3.5 px-4 text-right">
                      <div className="inline-flex items-center space-x-2">
                        <button
                          onClick={() => viewDetails(q.id)}
                          className="px-2.5 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-700 font-bold flex items-center space-x-1"
                        >
                          <Eye className="w-3.5 h-3.5" />
                          <span>Inspect</span>
                        </button>
                        {q.status !== "ORDER_CONFIRMED" && q.status !== "CANCELLED" && (
                          <button
                            onClick={() => {
                              setSelectedQuoteId(q.id);
                              setCancelOpen(true);
                            }}
                            className="p-1.5 rounded-lg text-slate-400 hover:text-red-600 hover:bg-red-50 transition"
                            title="Cancel Quotation"
                          >
                            <XCircle className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-400">
                    No quotation records found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Details & Revisions Modal */}
      {detailsOpen && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-4xl w-full max-h-[90vh] flex flex-col relative overflow-hidden">
            {/* Header */}
            <div className="p-5 border-b border-slate-200 flex items-center justify-between bg-slate-50">
              <div>
                <div className="flex items-center space-x-2">
                  <h3 className="text-base font-black text-slate-900 tracking-tight">
                    Quotation: {activeDetails?.quotation_number || "DRAFT"}
                  </h3>
                  {activeDetails && getStatusBadge(activeDetails.status)}
                </div>
                <p className="text-xs text-slate-500 mt-0.5">
                  Prepared by {activeDetails?.agent_name} &bull; Customer: {activeDetails?.customer_name} ({activeDetails?.customer_mobile})
                </p>
              </div>
              <button onClick={() => setDetailsOpen(false)} className="text-slate-400 hover:text-slate-700">
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Body */}
            {detailsLoading ? (
              <div className="p-12 text-center text-xs text-slate-400">Loading quotation snapshot...</div>
            ) : activeDetails ? (
              <div className="p-6 overflow-y-auto space-y-5 text-xs flex-1">
                {/* Revision Selector Tabs */}
                <div className="flex items-center space-x-2 border-b border-slate-200 pb-3">
                  <span className="font-bold text-slate-400 text-[10px] uppercase tracking-wider mr-2">
                    Revision Snapshots:
                  </span>
                  {activeDetails.revisions.map((rev, index) => (
                    <button
                      key={rev.id}
                      onClick={() => setSelectedRevIndex(index)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-bold transition flex items-center space-x-1.5 ${
                        selectedRevIndex === index
                          ? "bg-red-600 text-white shadow-sm"
                          : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                      }`}
                    >
                      <span>{rev.revision_label}</span>
                      {rev.is_superseded && (
                        <span className="text-[9px] px-1 py-0.2 bg-black/20 rounded">Superseded</span>
                      )}
                    </button>
                  ))}
                </div>

                {/* Active Revision Details */}
                {activeDetails.revisions[selectedRevIndex] && (
                  <div className="space-y-4">
                    {/* Action Bar for Active Revision */}
                    <div className="flex items-center justify-between bg-slate-50 p-3 rounded-xl border border-slate-200">
                      <div>
                        <span className="font-bold text-slate-800">
                          {activeDetails.revisions[selectedRevIndex].revision_label} Snapshot
                        </span>
                        <span className="text-slate-400 text-[10px] ml-2">
                          Issued on: {formatDateTime(activeDetails.revisions[selectedRevIndex].created_at)}
                        </span>
                      </div>
                      <div className="flex items-center space-x-2">
                        <button
                          onClick={() => downloadDoc(activeDetails.id, activeDetails.revisions[selectedRevIndex].id, "pdf")}
                          className="px-3 py-1.5 rounded-lg bg-white border border-slate-200 hover:bg-slate-100 text-slate-700 font-bold flex items-center space-x-1.5 transition shadow-sm"
                        >
                          <FileDown className="w-3.5 h-3.5 text-red-600" />
                          <span>PDF</span>
                        </button>
                        <button
                          onClick={() => downloadDoc(activeDetails.id, activeDetails.revisions[selectedRevIndex].id, "png")}
                          className="px-3 py-1.5 rounded-lg bg-white border border-slate-200 hover:bg-slate-100 text-slate-700 font-bold flex items-center space-x-1.5 transition shadow-sm"
                        >
                          <ImageIcon className="w-3.5 h-3.5 text-blue-600" />
                          <span>PNG</span>
                        </button>
                      </div>
                    </div>

                    {/* Items Table (Exact 7-column format) */}
                    <div className="border border-slate-200 rounded-xl overflow-hidden">
                      <table className="w-full text-left">
                        <thead className="bg-slate-900 text-white text-[10px] uppercase font-bold">
                          <tr>
                            <th className="py-2.5 px-3 text-center">S.No.</th>
                            <th className="py-2.5 px-3">Product</th>
                            <th className="py-2.5 px-3 text-center">SKU / Model No.</th>
                            <th className="py-2.5 px-3">Description</th>
                            <th className="py-2.5 px-3 text-center">Qty.</th>
                            <th className="py-2.5 px-3 text-right">Unit Price (₹)</th>
                            <th className="py-2.5 px-3 text-right">Total Price (₹)</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                          {activeDetails.revisions[selectedRevIndex].items.map((item, idx) => (
                            <tr key={item.id} className="hover:bg-slate-50/50">
                              <td className="py-2.5 px-3 text-center text-slate-500 font-bold">{idx + 1}</td>
                              <td className="py-2.5 px-3">
                                <div className="w-12 h-12 bg-white rounded-lg border border-slate-200 p-1 flex items-center justify-center overflow-hidden">
                                  {item.image_url ? (
                                    <img
                                      src={item.image_url}
                                      alt={item.product_name}
                                      className="w-full h-full object-contain"
                                    />
                                  ) : (
                                    <div className="text-[9px] font-bold text-slate-400">Livguard</div>
                                  )}
                                </div>
                              </td>
                              <td className="py-2.5 px-3 text-center font-mono font-bold text-red-600">{item.sku}</td>
                              <td className="py-2.5 px-3">
                                <div className="font-bold text-slate-900">{item.product_name}</div>
                                {item.description && (
                                  <div className="text-[10px] text-slate-500 mt-0.5 line-clamp-2">
                                    {item.description.replace(/\n/g, " • ")}
                                  </div>
                                )}
                              </td>
                              <td className="py-2.5 px-3 text-center font-bold text-slate-800">{item.quantity}</td>
                              <td className="py-2.5 px-3 text-right font-medium text-slate-700">{formatCurrency(item.unit_price)}</td>
                              <td className="py-2.5 px-3 text-right font-black text-slate-900">{formatCurrency(item.total_price)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>

                    {/* Totals Breakdown */}
                    <div className="flex justify-end">
                      <div className="w-72 bg-slate-50 border border-slate-200 rounded-xl p-3.5 space-y-2">
                        <div className="flex justify-between text-slate-600">
                          <span>Subtotal:</span>
                          <span className="font-bold text-slate-900">{formatCurrency(activeDetails.revisions[selectedRevIndex].subtotal)}</span>
                        </div>
                        {activeDetails.revisions[selectedRevIndex].discount_amount > 0 && (
                          <div className="flex justify-between text-emerald-600 font-semibold">
                            <span>Coupon Discount ({activeDetails.revisions[selectedRevIndex].coupon_code}):</span>
                            <span>-{formatCurrency(activeDetails.revisions[selectedRevIndex].discount_amount)}</span>
                          </div>
                        )}
                        <div className="flex justify-between text-slate-600">
                          <span>GST ({activeDetails.revisions[selectedRevIndex].tax_rate}%):</span>
                          <span className="font-bold text-slate-900">{formatCurrency(activeDetails.revisions[selectedRevIndex].tax_amount)}</span>
                        </div>
                        <div className="flex justify-between pt-2 border-t border-slate-200 text-sm font-black text-red-600">
                          <span>Grand Total:</span>
                          <span>{formatCurrency(activeDetails.revisions[selectedRevIndex].grand_total)}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ) : null}
          </div>
        </div>
      )}

      {/* Cancellation Modal */}
      {cancelOpen && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-sm w-full p-6 relative">
            <button onClick={() => setCancelOpen(false)} className="absolute top-5 right-5 text-slate-400 hover:text-slate-700">
              <X className="w-5 h-5" />
            </button>
            <h3 className="text-base font-black text-slate-900 tracking-tight">Cancel Quotation</h3>
            <p className="text-xs text-slate-500 mt-1">Provide a mandatory reason for the audit log.</p>

            <form onSubmit={handleCancelSubmit} className="mt-4 space-y-4 text-xs">
              <div>
                <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">Cancellation Reason *</label>
                <textarea
                  rows={3}
                  required
                  value={cancelReason}
                  onChange={(e) => setCancelReason(e.target.value)}
                  placeholder="e.g. Customer requested cancellation due to budget constraints"
                  className="mt-1 w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:ring-2 focus:ring-red-500 focus:bg-white"
                />
              </div>
              <div className="flex items-center justify-end space-x-2 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setCancelOpen(false)}
                  className="px-4 py-2 border border-slate-200 rounded-lg text-xs font-semibold text-slate-600 hover:bg-slate-50"
                >
                  Close
                </button>
                <button
                  type="submit"
                  disabled={cancelLoading}
                  className="px-5 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-xs font-bold disabled:opacity-50"
                >
                  {cancelLoading ? "Cancelling..." : "Confirm Cancellation"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
