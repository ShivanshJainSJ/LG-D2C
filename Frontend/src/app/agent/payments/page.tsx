"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  CreditCard,
  Send,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  ShieldAlert,
  Loader2,
} from "lucide-react";
import { api } from "@/lib/api";
import { formatCurrency, formatDateTime } from "@/lib/utils";

interface AgentQuotation {
  id: string;
  quotation_number: string;
  customer_name: string;
  status: string;
  grand_total: number;
}

interface PaymentReport {
  id: string;
  quotation_id: string;
  quotation_number: string | null;
  amount: number;
  payment_method: string;
  transaction_ref: string;
  status: "PENDING_REVIEW" | "VERIFIED" | "REJECTED";
  rejection_reason: string | null;
  payment_date: string;
  created_at: string;
}

export default function AgentPaymentsPage() {
  const searchParams = useSearchParams();
  const preselectQuoteId = searchParams.get("quote_id");

  const [eligibleQuotations, setEligibleQuotations] = useState<AgentQuotation[]>([]);
  const [reports, setReports] = useState<PaymentReport[]>([]);
  const [loading, setLoading] = useState(true);

  // Form State
  const [selectedQuoteId, setSelectedQuoteId] = useState("");
  const [paymentMethod, setPaymentMethod] = useState("UPI");
  const [transactionRef, setTransactionRef] = useState("");
  const [remarks, setRemarks] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [formSuccess, setFormSuccess] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [quotes, myReports] = await Promise.all([
        api.get<AgentQuotation[]>("/agent/quotations?status_filter=ISSUED"),
        api.get<PaymentReport[]>("/agent/payments/my-reports"),
      ]);
      setEligibleQuotations(quotes);
      setReports(myReports);

      if (preselectQuoteId) {
        setSelectedQuoteId(preselectQuoteId);
      } else if (quotes.length > 0) {
        setSelectedQuoteId(quotes[0].id);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [preselectQuoteId]);

  const selectedQuote = eligibleQuotations.find((q) => q.id === selectedQuoteId);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedQuoteId || !selectedQuote) {
      setFormError("Please select an issued quotation.");
      return;
    }
    if (!transactionRef.trim()) {
      setFormError("Transaction / UTR reference number is required.");
      return;
    }

    setFormError(null);
    setFormSuccess(null);
    setSubmitting(true);

    try {
      await api.post("/agent/payments/report", {
        quotation_id: selectedQuoteId,
        amount: selectedQuote.grand_total, // Enforce full payable amount
        payment_method: paymentMethod,
        transaction_ref: transactionRef.trim(),
        remarks: remarks || null,
      });

      setFormSuccess(
        `Payment report for ${selectedQuote.quotation_number} submitted! It is now pending central admin verification.`
      );
      setTransactionRef("");
      setRemarks("");
      fetchData();
    } catch (err: any) {
      setFormError(err.message || "Failed to submit payment report.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-black text-slate-900 tracking-tight">Report Customer Payment</h1>
        <p className="text-xs text-slate-500 mt-1">
          Submit verified bank / UPI transaction references for customer quotation settlement
        </p>
      </div>

      {/* Rules Notice */}
      <div className="bg-slate-900 text-white p-4 rounded-xl shadow-sm text-xs flex items-center space-x-3">
        <ShieldAlert className="w-5 h-5 text-red-500 shrink-0" />
        <div>
          <strong className="text-red-400">Strict Verification Policy:</strong>
          <span className="text-slate-300 ml-1.5">
            Reporting a payment submits it to the central Admin review queue. Payments are only confirmed once verified by Livguard central administration. Quoted amounts must be settled in full.
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Form Column */}
        <div className="lg:col-span-5">
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
            <h2 className="text-xs font-black uppercase tracking-wider text-slate-800 flex items-center space-x-2">
              <CreditCard className="w-4 h-4 text-red-600" />
              <span>Payment Details Form</span>
            </h2>

            {formSuccess && (
              <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl flex items-center space-x-2 text-xs text-emerald-800 font-semibold">
                <CheckCircle className="w-4 h-4 text-emerald-600 shrink-0" />
                <span>{formSuccess}</span>
              </div>
            )}

            {formError && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-xl flex items-center space-x-2 text-xs text-red-700 font-semibold">
                <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
                <span>{formError}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4 text-xs">
              <div>
                <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                  Select Issued Quotation *
                </label>
                {eligibleQuotations.length > 0 ? (
                  <select
                    required
                    value={selectedQuoteId}
                    onChange={(e) => setSelectedQuoteId(e.target.value)}
                    className="mt-1 w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg font-bold text-slate-900 focus:ring-2 focus:ring-red-500 focus:bg-white"
                  >
                    {eligibleQuotations.map((q) => (
                      <option key={q.id} value={q.id}>
                        {q.quotation_number} - {q.customer_name} ({formatCurrency(q.grand_total)})
                      </option>
                    ))}
                  </select>
                ) : (
                  <div className="mt-1 p-3 bg-slate-50 rounded-lg border border-slate-200 text-slate-400 text-xs">
                    No issued quotations available for payment. Issue a quotation first.
                  </div>
                )}
              </div>

              {selectedQuote && (
                <div className="p-3 bg-red-50 border border-red-100 rounded-xl text-xs flex justify-between items-center">
                  <span className="font-bold text-red-900">Full Payable Amount:</span>
                  <span className="font-black text-red-600 text-sm">
                    {formatCurrency(selectedQuote.grand_total)}
                  </span>
                </div>
              )}

              <div>
                <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                  Payment Method *
                </label>
                <select
                  value={paymentMethod}
                  onChange={(e) => setPaymentMethod(e.target.value)}
                  className="mt-1 w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg font-semibold text-slate-900 focus:ring-2 focus:ring-red-500 focus:bg-white"
                >
                  <option value="UPI">UPI (Google Pay, PhonePe, Paytm)</option>
                  <option value="NEFT_RTGS">NEFT / RTGS Bank Transfer</option>
                  <option value="NET_BANKING">Net Banking</option>
                  <option value="CHEQUE">Cheque / Demand Draft</option>
                  <option value="CASH">Cash Deposit</option>
                </select>
              </div>

              <div>
                <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                  Transaction Reference / UTR Number *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. UPI329847293847 or HDFC120934"
                  value={transactionRef}
                  onChange={(e) => setTransactionRef(e.target.value.toUpperCase())}
                  className="mt-1 w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg font-mono font-black text-slate-900 tracking-wider focus:ring-2 focus:ring-red-500 focus:bg-white"
                />
              </div>

              <div>
                <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                  Remarks / Deposit Location
                </label>
                <input
                  type="text"
                  placeholder="e.g. Deposited into Livguard HDFC current A/C"
                  value={remarks}
                  onChange={(e) => setRemarks(e.target.value)}
                  className="mt-1 w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:ring-2 focus:ring-red-500 focus:bg-white"
                />
              </div>

              <button
                type="submit"
                disabled={submitting || eligibleQuotations.length === 0}
                className="w-full py-3 bg-red-600 hover:bg-red-700 text-white font-black text-xs uppercase tracking-wider rounded-xl shadow-lg shadow-red-600/30 transition flex items-center justify-center space-x-2 disabled:opacity-50"
              >
                {submitting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Submitting Report...</span>
                  </>
                ) : (
                  <>
                    <Send className="w-4 h-4" />
                    <span>Submit Payment for Review</span>
                  </>
                )}
              </button>
            </form>
          </div>
        </div>

        {/* Reports History Column */}
        <div className="lg:col-span-7">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="p-4 border-b border-slate-200 bg-slate-50">
              <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                My Reported Payments ({reports.length})
              </h3>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-400 uppercase text-[9px] font-bold">
                  <tr>
                    <th className="py-2.5 px-3">Quotation</th>
                    <th className="py-2.5 px-3">Amount</th>
                    <th className="py-2.5 px-3">Transaction Ref</th>
                    <th className="py-2.5 px-3">Status</th>
                    <th className="py-2.5 px-3">Reported</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {loading ? (
                    <tr>
                      <td colSpan={5} className="py-8 text-center text-slate-400">
                        Loading reports...
                      </td>
                    </tr>
                  ) : reports.length > 0 ? (
                    reports.map((r) => (
                      <tr key={r.id} className="hover:bg-slate-50/50">
                        <td className="py-3 px-3 font-mono font-bold text-red-600">
                          {r.quotation_number || "Draft Ref"}
                        </td>
                        <td className="py-3 px-3 font-black text-slate-900">{formatCurrency(r.amount)}</td>
                        <td className="py-3 px-3 font-mono font-semibold text-slate-700">{r.transaction_ref}</td>
                        <td className="py-3 px-3">
                          {r.status === "PENDING_REVIEW" && (
                            <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 font-bold text-[10px]">
                              <Clock className="w-3 h-3 text-amber-500" />
                              <span>Pending Review</span>
                            </span>
                          )}
                          {r.status === "VERIFIED" && (
                            <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 font-bold text-[10px]">
                              <CheckCircle className="w-3 h-3 text-emerald-500" />
                              <span>Verified</span>
                            </span>
                          )}
                          {r.status === "REJECTED" && (
                            <div>
                              <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full bg-red-50 text-red-700 font-bold text-[10px]">
                                <XCircle className="w-3 h-3 text-red-500" />
                                <span>Rejected</span>
                              </span>
                              {r.rejection_reason && (
                                <p className="text-[10px] text-red-600 mt-1 italic">{r.rejection_reason}</p>
                              )}
                            </div>
                          )}
                        </td>
                        <td className="py-3 px-3 text-slate-400 font-medium">{formatDateTime(r.created_at)}</td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={5} className="py-8 text-center text-slate-400">
                        No payment reports submitted yet.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
