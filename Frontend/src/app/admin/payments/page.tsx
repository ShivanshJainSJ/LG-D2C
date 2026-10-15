"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  CreditCard,
  CheckCircle,
  XCircle,
  Clock,
  Search,
  Filter,
  AlertCircle,
  ArrowRight,
  ShieldCheck,
  X,
  FileCheck,
} from "lucide-react";
import { api } from "@/lib/api";
import { formatCurrency, formatDateTime } from "@/lib/utils";

interface Payment {
  id: string;
  quotation_id: string;
  quotation_number: string | null;
  reported_by_name: string;
  amount: number;
  payment_date: string;
  payment_method: string;
  transaction_ref: string;
  evidence_url: string | null;
  status: "PENDING_REVIEW" | "VERIFIED" | "REJECTED";
  rejection_reason: string | null;
  verified_by_name: string | null;
  verified_at: string | null;
  remarks: string | null;
  created_at: string;
}

export default function AdminPaymentsPage() {
  const [payments, setPayments] = useState<Payment[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>("PENDING_REVIEW");

  // Action Modal
  const [actionModalOpen, setActionModalOpen] = useState(false);
  const [selectedPayment, setSelectedPayment] = useState<Payment | null>(null);
  const [actionType, setActionType] = useState<"VERIFY" | "REJECT">("VERIFY");
  const [rejectionReason, setRejectionReason] = useState("");
  const [actionRemarks, setActionRemarks] = useState("");
  const [actionLoading, setActionLoading] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const fetchPayments = async () => {
    try {
      setLoading(true);
      let url = "/admin/payments";
      if (statusFilter) url += `?status_filter=${statusFilter}`;
      const data = await api.get<Payment[]>(url);
      setPayments(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPayments();
  }, [statusFilter]);

  const openActionModal = (p: Payment, type: "VERIFY" | "REJECT") => {
    setSelectedPayment(p);
    setActionType(type);
    setRejectionReason("");
    setActionRemarks("");
    setActionError(null);
    setActionModalOpen(true);
  };

  const handleActionSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedPayment) return;
    setActionError(null);
    setActionLoading(true);

    try {
      if (actionType === "VERIFY") {
        await api.put(`/admin/payments/${selectedPayment.id}/verify`, {
          status: "VERIFIED",
          remarks: actionRemarks || "Payment verified by finance administrator.",
        });
      } else {
        if (!rejectionReason.trim()) {
          setActionError("Rejection reason is mandatory.");
          setActionLoading(false);
          return;
        }
        await api.put(`/admin/payments/${selectedPayment.id}/verify`, {
          status: "REJECTED",
          rejection_reason: rejectionReason.trim(),
          remarks: actionRemarks,
        });
      }
      setActionModalOpen(false);
      fetchPayments();
    } catch (err: any) {
      setActionError(err.message || "Failed to process payment review.");
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-black text-slate-900 tracking-tight">Payment Verification Queue</h1>
        <p className="text-xs text-slate-500 mt-1">
          Review incoming agent payment reports, verify bank transaction references, or reject with documented reasons
        </p>
      </div>

      {/* Rules Notice */}
      <div className="bg-amber-50 border-l-4 border-amber-500 p-4 rounded-r-xl shadow-sm text-xs">
        <strong className="text-amber-900">Payment Workflow Requirement:</strong>
        <span className="text-amber-800 ml-1.5">
          Payment verification and order confirmation are separate operations. Verifying a payment allows subsequent order acceptance, but does not automatically confirm the order.
        </span>
      </div>

      {/* Status Filter Tabs */}
      <div className="flex items-center space-x-2 border-b border-slate-200 pb-3">
        {[
          { label: "Pending Review", value: "PENDING_REVIEW" },
          { label: "Verified", value: "VERIFIED" },
          { label: "Rejected", value: "REJECTED" },
          { label: "All Records", value: "" },
        ].map((tab) => (
          <button
            key={tab.label}
            onClick={() => setStatusFilter(tab.value)}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition ${
              statusFilter === tab.value
                ? "bg-slate-900 text-white shadow-sm"
                : "bg-white border border-slate-200 text-slate-600 hover:bg-slate-50"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Payments Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase tracking-wider text-[10px] font-bold">
              <tr>
                <th className="py-3 px-4">Quotation Ref</th>
                <th className="py-3 px-4">Reported By</th>
                <th className="py-3 px-4">Amount</th>
                <th className="py-3 px-4">Payment Method</th>
                <th className="py-3 px-4">Transaction Ref</th>
                <th className="py-3 px-4">Reported At</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4 text-right">Review Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading ? (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-slate-400">
                    Loading payment queue...
                  </td>
                </tr>
              ) : payments.length > 0 ? (
                payments.map((p) => (
                  <tr key={p.id} className="hover:bg-slate-50/80 transition">
                    <td className="py-3.5 px-4 font-mono font-bold text-red-600">
                      {p.quotation_number || "Draft Ref"}
                    </td>
                    <td className="py-3.5 px-4 font-bold text-slate-900">{p.reported_by_name}</td>
                    <td className="py-3.5 px-4 font-black text-slate-900 text-sm">
                      {formatCurrency(p.amount)}
                    </td>
                    <td className="py-3.5 px-4 font-semibold text-slate-700">{p.payment_method}</td>
                    <td className="py-3.5 px-4 font-mono text-slate-800 font-bold">{p.transaction_ref}</td>
                    <td className="py-3.5 px-4 text-slate-400 font-medium">{formatDateTime(p.created_at)}</td>
                    <td className="py-3.5 px-4">
                      {p.status === "PENDING_REVIEW" && (
                        <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 font-bold text-[10px]">
                          <Clock className="w-3 h-3 text-amber-500" />
                          <span>Pending</span>
                        </span>
                      )}
                      {p.status === "VERIFIED" && (
                        <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 font-bold text-[10px]">
                          <CheckCircle className="w-3 h-3 text-emerald-500" />
                          <span>Verified</span>
                        </span>
                      )}
                      {p.status === "REJECTED" && (
                        <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full bg-red-50 text-red-700 font-bold text-[10px]">
                          <XCircle className="w-3 h-3 text-red-500" />
                          <span>Rejected</span>
                        </span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      {p.status === "PENDING_REVIEW" ? (
                        <div className="inline-flex items-center space-x-1.5">
                          <button
                            onClick={() => openActionModal(p, "VERIFY")}
                            className="px-2.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-bold transition flex items-center space-x-1 shadow-sm"
                          >
                            <CheckCircle className="w-3.5 h-3.5" />
                            <span>Verify</span>
                          </button>
                          <button
                            onClick={() => openActionModal(p, "REJECT")}
                            className="px-2.5 py-1.5 rounded-lg border border-red-200 text-red-600 hover:bg-red-50 font-bold transition flex items-center space-x-1"
                          >
                            <XCircle className="w-3.5 h-3.5" />
                            <span>Reject</span>
                          </button>
                        </div>
                      ) : p.status === "VERIFIED" ? (
                        <Link
                          href="/admin/orders"
                          className="px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-white font-bold inline-flex items-center space-x-1 transition"
                        >
                          <FileCheck className="w-3.5 h-3.5 text-emerald-400" />
                          <span>Confirm Order</span>
                        </Link>
                      ) : (
                        <span className="text-[10px] text-red-500 italic font-semibold">
                          Reason: {p.rejection_reason}
                        </span>
                      )}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-slate-400">
                    No payment reports in this queue.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Review Verification / Rejection Modal */}
      {actionModalOpen && selectedPayment && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-md w-full p-6 relative">
            <button onClick={() => setActionModalOpen(false)} className="absolute top-5 right-5 text-slate-400 hover:text-slate-700">
              <X className="w-5 h-5" />
            </button>

            <h3 className="text-base font-black text-slate-900 tracking-tight">
              {actionType === "VERIFY" ? "Verify Customer Payment" : "Reject Payment Report"}
            </h3>
            <p className="text-xs text-slate-500 mt-1">
              Quotation: {selectedPayment.quotation_number} &bull; Amount: {formatCurrency(selectedPayment.amount)}
            </p>

            {actionError && (
              <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center space-x-2 text-xs text-red-700">
                <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
                <span>{actionError}</span>
              </div>
            )}

            <div className="mt-4 p-3 bg-slate-50 border border-slate-200 rounded-xl space-y-1.5 text-xs">
              <div className="flex justify-between">
                <span className="text-slate-500 font-semibold">Payment Method:</span>
                <span className="font-bold text-slate-800">{selectedPayment.payment_method}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500 font-semibold">Transaction Reference:</span>
                <span className="font-mono font-bold text-red-600">{selectedPayment.transaction_ref}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500 font-semibold">Reported By Agent:</span>
                <span className="font-bold text-slate-800">{selectedPayment.reported_by_name}</span>
              </div>
            </div>

            <form onSubmit={handleActionSubmit} className="mt-5 space-y-4 text-xs">
              {actionType === "REJECT" ? (
                <div>
                  <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                    Rejection Reason (Mandatory) *
                  </label>
                  <textarea
                    rows={3}
                    required
                    value={rejectionReason}
                    onChange={(e) => setRejectionReason(e.target.value)}
                    placeholder="e.g. Transaction reference does not match bank credits or amount mismatch"
                    className="mt-1 w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:ring-2 focus:ring-red-500 focus:bg-white"
                  />
                </div>
              ) : null}

              <div>
                <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                  Administrative Remarks
                </label>
                <input
                  type="text"
                  value={actionRemarks}
                  onChange={(e) => setActionRemarks(e.target.value)}
                  placeholder="e.g. Verified in Livguard HDFC current account"
                  className="mt-1 w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:ring-2 focus:ring-red-500 focus:bg-white"
                />
              </div>

              <div className="flex items-center justify-end space-x-3 pt-4 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setActionModalOpen(false)}
                  className="px-4 py-2 border border-slate-200 rounded-lg text-xs font-semibold text-slate-600 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className={`px-5 py-2 text-white rounded-lg text-xs font-bold shadow-md disabled:opacity-50 ${
                    actionType === "VERIFY"
                      ? "bg-emerald-600 hover:bg-emerald-700 shadow-emerald-600/30"
                      : "bg-red-600 hover:bg-red-700 shadow-red-600/30"
                  }`}
                >
                  {actionLoading
                    ? "Processing..."
                    : actionType === "VERIFY"
                    ? "Confirm Payment Verification"
                    : "Confirm Rejection"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
