"use client";

import { useEffect, useState } from "react";
import {
  ShoppingBag,
  FileCheck,
  Download,
  Calendar,
  FileDown,
  Image as ImageIcon,
  CheckCircle2,
  Clock,
  Plus,
  X,
  AlertCircle,
} from "lucide-react";
import { api } from "@/lib/api";
import { formatCurrency, formatDateTime, formatDate } from "@/lib/utils";

interface Order {
  id: string;
  order_number: string;
  quotation_id: string;
  quotation_number: string;
  confirmed_by_name: string;
  confirmed_amount: number;
  order_date: string;
  expected_delivery_date: string | null;
  remarks: string | null;
  status: string;
  created_at: string;
}

interface QuotationEligible {
  id: string;
  quotation_number: string;
  customer_name: string;
  grand_total: number;
  status: string;
}

export default function AdminOrdersPage() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);

  // New Order Confirmation Modal
  const [confirmModalOpen, setConfirmModalOpen] = useState(false);
  const [eligibleQuotes, setEligibleQuotes] = useState<QuotationEligible[]>([]);
  const [selectedQuoteId, setSelectedQuoteId] = useState("");
  const [expectedDate, setExpectedDate] = useState("");
  const [remarks, setRemarks] = useState("");
  const [confirmLoading, setConfirmLoading] = useState(false);
  const [confirmError, setConfirmError] = useState<string | null>(null);

  const fetchOrders = async () => {
    try {
      setLoading(true);
      const data = await api.get<Order[]>("/admin/orders");
      setOrders(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOrders();
  }, []);

  const openConfirmModal = async () => {
    setConfirmError(null);
    setSelectedQuoteId("");
    setRemarks("");
    setExpectedDate("");
    setConfirmModalOpen(true);

    try {
      // Fetch quotations with status PAYMENT_VERIFIED
      const data = await api.get<{ items: QuotationEligible[] }>("/admin/quotations?status_filter=PAYMENT_VERIFIED");
      setEligibleQuotes(data.items);
      if (data.items.length > 0) {
        setSelectedQuoteId(data.items[0].id);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleOrderSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedQuoteId) {
      setConfirmError("Please select a verified quotation.");
      return;
    }
    setConfirmError(null);
    setConfirmLoading(true);

    try {
      await api.post("/admin/orders", {
        quotation_id: selectedQuoteId,
        expected_delivery_date: expectedDate ? new Date(expectedDate).toISOString() : null,
        remarks: remarks || "Order confirmed by central administrator.",
      });
      setConfirmModalOpen(false);
      fetchOrders();
    } catch (err: any) {
      setConfirmError(err.message || "Failed to confirm order.");
    } finally {
      setConfirmLoading(false);
    }
  };

  const downloadOrderDoc = async (orderId: string, format: "pdf" | "png") => {
    try {
      const blob = await api.get<Blob>(`/admin/orders/${orderId}/${format}`);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `Livguard_Order_Confirmation.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err: any) {
      alert("Failed to download order document: " + err.message);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight">Confirmed Orders Master</h1>
          <p className="text-xs text-slate-500 mt-1">
            Accept verified payments into official confirmed orders and issue signed Order Received documents
          </p>
        </div>
        <button
          onClick={openConfirmModal}
          className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold flex items-center space-x-1.5 transition shadow-md shadow-emerald-600/20"
        >
          <Plus className="w-4 h-4" />
          <span>Confirm Verified Order</span>
        </button>
      </div>

      {/* Orders Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase tracking-wider text-[10px] font-bold">
              <tr>
                <th className="py-3 px-4">Order Number</th>
                <th className="py-3 px-4">Quotation Ref</th>
                <th className="py-3 px-4">Confirmed Amount</th>
                <th className="py-3 px-4">Confirmed By</th>
                <th className="py-3 px-4">Order Date</th>
                <th className="py-3 px-4">Expected Delivery</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4 text-right">Official Document</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading ? (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-slate-400">
                    Loading confirmed orders...
                  </td>
                </tr>
              ) : orders.length > 0 ? (
                orders.map((o) => (
                  <tr key={o.id} className="hover:bg-slate-50/80 transition">
                    <td className="py-3.5 px-4 font-mono font-black text-emerald-600 text-sm">
                      {o.order_number}
                    </td>
                    <td className="py-3.5 px-4 font-mono font-bold text-red-600">{o.quotation_number}</td>
                    <td className="py-3.5 px-4 font-black text-slate-900 text-sm">
                      {formatCurrency(o.confirmed_amount)}
                    </td>
                    <td className="py-3.5 px-4 font-semibold text-slate-700">{o.confirmed_by_name}</td>
                    <td className="py-3.5 px-4 text-slate-600">{formatDate(o.order_date)}</td>
                    <td className="py-3.5 px-4 text-slate-500">{o.expected_delivery_date ? formatDate(o.expected_delivery_date) : "Pending"}</td>
                    <td className="py-3.5 px-4">
                      <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-700 font-bold text-[10px]">
                        <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                        <span>{o.status}</span>
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <div className="inline-flex items-center space-x-1.5">
                        <button
                          onClick={() => downloadOrderDoc(o.id, "pdf")}
                          className="px-2.5 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-700 font-bold flex items-center space-x-1 shadow-sm"
                          title="Download Order Confirmation PDF"
                        >
                          <FileDown className="w-3.5 h-3.5 text-red-600" />
                          <span>PDF</span>
                        </button>
                        <button
                          onClick={() => downloadOrderDoc(o.id, "png")}
                          className="px-2.5 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-700 font-bold flex items-center space-x-1 shadow-sm"
                          title="Download Order Confirmation PNG"
                        >
                          <ImageIcon className="w-3.5 h-3.5 text-blue-600" />
                          <span>PNG</span>
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-slate-400">
                    No confirmed orders recorded yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Confirmation Modal */}
      {confirmModalOpen && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-md w-full p-6 relative">
            <button onClick={() => setConfirmModalOpen(false)} className="absolute top-5 right-5 text-slate-400 hover:text-slate-700">
              <X className="w-5 h-5" />
            </button>

            <h3 className="text-base font-black text-slate-900 tracking-tight">Complete Order Received Acceptance</h3>
            <p className="text-xs text-slate-500 mt-1">
              Select a quotation with verified payment to assign an official sequential Order Number.
            </p>

            {confirmError && (
              <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center space-x-2 text-xs text-red-700">
                <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
                <span>{confirmError}</span>
              </div>
            )}

            <form onSubmit={handleOrderSubmit} className="mt-5 space-y-4 text-xs">
              <div>
                <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                  Verified Quotation *
                </label>
                {eligibleQuotes.length > 0 ? (
                  <select
                    required
                    value={selectedQuoteId}
                    onChange={(e) => setSelectedQuoteId(e.target.value)}
                    className="mt-1 w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg font-bold text-slate-900 focus:ring-2 focus:ring-emerald-500 focus:bg-white"
                  >
                    {eligibleQuotes.map((q) => (
                      <option key={q.id} value={q.id}>
                        {q.quotation_number} &bull; {q.customer_name} &bull; {formatCurrency(q.grand_total)}
                      </option>
                    ))}
                  </select>
                ) : (
                  <div className="mt-1 p-3 bg-slate-50 rounded-lg text-slate-500 border border-slate-200">
                    No verified quotations awaiting order confirmation. Verify a payment in the Review Queue first.
                  </div>
                )}
              </div>

              <div>
                <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                  Expected Delivery Date (Optional)
                </label>
                <input
                  type="date"
                  value={expectedDate}
                  onChange={(e) => setExpectedDate(e.target.value)}
                  className="mt-1 w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:bg-white"
                />
              </div>

              <div>
                <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                  Internal Remarks
                </label>
                <input
                  type="text"
                  value={remarks}
                  onChange={(e) => setRemarks(e.target.value)}
                  placeholder="e.g. Priority dispatch via Gurgaon warehouse"
                  className="mt-1 w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:bg-white"
                />
              </div>

              <div className="flex items-center justify-end space-x-3 pt-4 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setConfirmModalOpen(false)}
                  className="px-4 py-2 border border-slate-200 rounded-lg text-xs font-semibold text-slate-600 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={confirmLoading || eligibleQuotes.length === 0}
                  className="px-5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold shadow-md shadow-emerald-600/30 disabled:opacity-50"
                >
                  {confirmLoading ? "Confirming..." : "Issue Confirmed Order"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
