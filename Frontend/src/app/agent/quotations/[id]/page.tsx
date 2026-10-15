"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  FileText,
  FileDown,
  Image as ImageIcon,
  ArrowLeft,
  Clock,
  Layers,
  Edit,
  AlertCircle,
  CheckCircle,
  Plus,
  Trash2,
  X,
  CreditCard,
} from "lucide-react";
import { api } from "@/lib/api";
import { formatCurrency, formatDateTime } from "@/lib/utils";

interface QuotationItem {
  id: string;
  product_id: string;
  sku: string;
  product_name: string;
  description: string | null;
  image_url?: string | null;
  unit_price: number;
  quantity: number;
  total_price: number;
}

interface Revision {
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
  items: QuotationItem[];
}

interface QuotationDetail {
  id: string;
  quotation_number: string;
  current_revision_number: number;
  customer_name: string;
  customer_mobile: string;
  customer_email: string | null;
  customer_address: string | null;
  status: string;
  created_at: string;
  revisions: Revision[];
}

interface ActiveProduct {
  id: string;
  sku: string;
  name: string;
  unit_price: number;
}

export default function AgentQuotationDetailPage() {
  const params = useParams();
  const router = useRouter();
  const quoteId = params.id as string;

  const [quotation, setQuotation] = useState<QuotationDetail | null>(null);
  const [selectedRevIndex, setSelectedRevIndex] = useState(0);
  const [loading, setLoading] = useState(true);

  // Revision Modal State
  const [revisionModalOpen, setRevisionModalOpen] = useState(false);
  const [availableProducts, setAvailableProducts] = useState<ActiveProduct[]>([]);
  const [revItems, setRevItems] = useState<{ product_id: string; quantity: number }[]>([]);
  const [revCoupon, setRevCoupon] = useState("");
  const [selectedProdId, setSelectedProdId] = useState("");
  const [selectedQty, setSelectedQty] = useState(1);
  const [revLoading, setRevLoading] = useState(false);
  const [revError, setRevError] = useState<string | null>(null);

  const fetchQuotation = async () => {
    try {
      setLoading(true);
      const data = await api.get<QuotationDetail>(`/agent/quotations/${quoteId}`);
      setQuotation(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (quoteId) fetchQuotation();
  }, [quoteId]);

  const downloadDoc = async (revId: string, format: "pdf" | "png") => {
    try {
      const blob = await api.get<Blob>(`/agent/quotations/${quoteId}/revisions/${revId}/${format}`);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `Livguard_Quotation_${quotation?.quotation_number || "Doc"}_Rev.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err: any) {
      alert("Download failed: " + err.message);
    }
  };

  const openRevisionModal = async () => {
    if (!quotation) return;
    setRevError(null);
    setRevisionModalOpen(true);

    try {
      const prods = await api.get<ActiveProduct[]>("/agent/products");
      setAvailableProducts(prods);
      if (prods.length > 0) setSelectedProdId(prods[0].id);

      // Pre-populate with latest revision items
      const latestRev = quotation.revisions[0];
      setRevItems(latestRev.items.map((i) => ({ product_id: i.product_id, quantity: i.quantity })));
      setRevCoupon(latestRev.coupon_code || "");
    } catch (err) {
      console.error(err);
    }
  };

  const handleAddRevItem = () => {
    if (!selectedProdId || selectedQty <= 0) return;
    const existing = revItems.findIndex((i) => i.product_id === selectedProdId);
    if (existing >= 0) {
      const copy = [...revItems];
      copy[existing].quantity += selectedQty;
      setRevItems(copy);
    } else {
      setRevItems([...revItems, { product_id: selectedProdId, quantity: selectedQty }]);
    }
    setSelectedQty(1);
  };

  const handleRemoveRevItem = (idx: number) => {
    setRevItems(revItems.filter((_, i) => i !== idx));
  };

  const handleRevisionSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!quotation || revItems.length === 0) {
      setRevError("At least one product line item is required.");
      return;
    }
    setRevLoading(true);
    setRevError(null);

    try {
      await api.post(`/agent/quotations/${quotation.id}/revise`, {
        customer_name: quotation.customer_name,
        customer_mobile: quotation.customer_mobile,
        customer_email: quotation.customer_email,
        customer_address: quotation.customer_address,
        items: revItems,
        coupon_code: revCoupon || null,
      });
      setRevisionModalOpen(false);
      fetchQuotation();
    } catch (err: any) {
      setRevError(err.message || "Failed to create revision.");
    } finally {
      setRevLoading(false);
    }
  };

  if (loading) {
    return <div className="p-12 text-center text-xs text-slate-400">Loading quotation details...</div>;
  }

  if (!quotation) {
    return <div className="p-12 text-center text-xs text-red-600">Quotation not found.</div>;
  }

  const activeRevision = quotation.revisions[selectedRevIndex];
  const isFrozen = ["PAYMENT_PENDING", "PAYMENT_VERIFIED", "ORDER_CONFIRMED", "CANCELLED"].includes(quotation.status);

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Back button & Action Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <Link
          href="/agent/quotations"
          className="inline-flex items-center space-x-1.5 text-xs font-bold text-slate-500 hover:text-slate-900 transition"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Quotations</span>
        </Link>

        <div className="flex items-center space-x-2">
          {quotation.status === "ISSUED" && (
            <Link
              href={`/agent/payments?quote_id=${quotation.id}`}
              className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs flex items-center space-x-1 shadow-sm transition"
            >
              <CreditCard className="w-3.5 h-3.5" />
              <span>Report Payment</span>
            </Link>
          )}

          <button
            onClick={openRevisionModal}
            disabled={isFrozen}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-bold flex items-center space-x-1.5 transition ${
              isFrozen
                ? "bg-slate-200 text-slate-400 cursor-not-allowed"
                : "bg-slate-900 hover:bg-slate-800 text-white shadow-sm"
            }`}
          >
            <Edit className="w-3.5 h-3.5" />
            <span>Create Revision</span>
          </button>
        </div>
      </div>

      {/* Editing Restriction Alert if Frozen */}
      {isFrozen && (
        <div className="p-4 bg-amber-50 border-l-4 border-amber-500 rounded-r-xl text-xs flex items-center space-x-3 text-amber-900">
          <AlertCircle className="w-5 h-5 text-amber-600 shrink-0" />
          <div>
            <strong>Quotation Frozen for Revisions:</strong>
            <span className="ml-1 text-amber-800">
              {quotation.status === "PAYMENT_PENDING" && "A customer payment has been reported and is under review by Admin."}
              {quotation.status === "PAYMENT_VERIFIED" && "Payment has been verified. Order confirmation is pending."}
              {quotation.status === "ORDER_CONFIRMED" && "Order is officially confirmed. Confirmed quotations are permanently locked."}
              {quotation.status === "CANCELLED" && "This quotation has been cancelled."}
            </span>
          </div>
        </div>
      )}

      {/* Main Quotation Card */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        {/* Document Header Bar */}
        <div className="p-5 border-b border-slate-200 bg-slate-50 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-xl font-black text-slate-900 tracking-tight">
                {quotation.quotation_number || "DRAFT"}
              </h1>
              <span className="px-2 py-0.5 rounded-full bg-slate-900 text-white font-bold text-[10px]">
                {quotation.status}
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Customer: <strong className="text-slate-800">{quotation.customer_name}</strong> &bull; Mobile: {quotation.customer_mobile}
            </p>
          </div>

          {activeRevision && (
            <div className="flex items-center space-x-2">
              <button
                onClick={() => downloadDoc(activeRevision.id, "pdf")}
                className="px-3 py-1.5 rounded-lg bg-white border border-slate-200 hover:bg-slate-100 text-slate-700 font-bold text-xs flex items-center space-x-1.5 transition shadow-sm"
              >
                <FileDown className="w-3.5 h-3.5 text-red-600" />
                <span>Download PDF</span>
              </button>
              <button
                onClick={() => downloadDoc(activeRevision.id, "png")}
                className="px-3 py-1.5 rounded-lg bg-white border border-slate-200 hover:bg-slate-100 text-slate-700 font-bold text-xs flex items-center space-x-1.5 transition shadow-sm"
              >
                <ImageIcon className="w-3.5 h-3.5 text-blue-600" />
                <span>Download PNG</span>
              </button>
            </div>
          )}
        </div>

        {/* Revision Selector Tabs */}
        <div className="px-5 pt-4 border-b border-slate-100 flex items-center space-x-2 overflow-x-auto">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mr-2 shrink-0">
            Version History:
          </span>
          {quotation.revisions.map((rev, idx) => (
            <button
              key={rev.id}
              onClick={() => setSelectedRevIndex(idx)}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition flex items-center space-x-1.5 shrink-0 ${
                selectedRevIndex === idx
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

        {/* Active Revision Snapshot */}
        {activeRevision && (
          <div className="p-5 sm:p-6 space-y-6 text-xs">
            {/* Document Branded Header */}
            <div className="flex flex-col sm:flex-row justify-between items-center border-b border-slate-200 pb-4 gap-4">
              <div className="flex items-center gap-3">
                <div className="h-12 w-28 bg-black rounded-lg p-1.5 flex items-center justify-center shadow-sm">
                  <img
                    src="/assets/livguard_logo.jpg"
                    alt="Livguard"
                    className="max-h-full max-w-full object-contain"
                  />
                </div>
                <div>
                  <h2 className="text-base font-black text-slate-900 tracking-tight uppercase">LIVGUARD QUOTATION</h2>
                  <p className="text-[11px] text-slate-500 font-semibold">Powering the homes of tomorrow</p>
                </div>
              </div>

              <div className="shrink-0">
                <img
                  src="/assets/livguard_banner.jpg"
                  alt="Livguard Inverters & Batteries"
                  className="h-12 sm:h-14 w-auto max-w-[280px] rounded-lg object-cover border border-slate-200 shadow-sm"
                />
              </div>
            </div>

            {/* Meta Info Panel */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 bg-slate-50 p-4 rounded-xl border border-slate-200">
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-red-600 block mb-1">
                  Customer Information
                </span>
                <p className="font-bold text-slate-900">{quotation.customer_name}</p>
                <p className="text-slate-600 mt-0.5">Mobile: {quotation.customer_mobile}</p>
                {quotation.customer_email && <p className="text-slate-600">Email: {quotation.customer_email}</p>}
                {quotation.customer_address && <p className="text-slate-600">Address: {quotation.customer_address}</p>}
              </div>
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-red-600 block mb-1">
                  Document Metadata
                </span>
                <p className="text-slate-700">
                  Version: <strong>{activeRevision.revision_label}</strong>
                  {activeRevision.is_superseded ? " (Historical Snapshot)" : " (Current Active Version)"}
                </p>
                <p className="text-slate-700 mt-0.5">Issued: {formatDateTime(activeRevision.created_at)}</p>
                {activeRevision.coupon_code && (
                  <p className="text-emerald-700 font-semibold mt-0.5">
                    Promotional Coupon: {activeRevision.coupon_code}
                  </p>
                )}
              </div>
            </div>

            {/* Line Items Table (Exact Reference Format) */}
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
                  {activeRevision.items.map((item, idx) => (
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
                      <td className="py-2.5 px-3 text-center font-mono font-bold text-red-600">
                        {item.sku}
                      </td>
                      <td className="py-2.5 px-3">
                        <div className="font-bold text-slate-900">{item.product_name}</div>
                        {item.description && (
                          <div className="text-[10px] text-slate-500 mt-0.5 line-clamp-2">
                            {item.description.replace(/\n/g, " • ")}
                          </div>
                        )}
                      </td>
                      <td className="py-2.5 px-3 text-center font-bold text-slate-800">{item.quantity}</td>
                      <td className="py-2.5 px-3 text-right font-medium text-slate-700">
                        {formatCurrency(item.unit_price)}
                      </td>
                      <td className="py-2.5 px-3 text-right font-black text-slate-900">
                        {formatCurrency(item.total_price)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Totals Summary */}
            <div className="flex justify-end">
              <div className="w-80 bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-2">
                <div className="flex justify-between text-slate-600">
                  <span>Subtotal:</span>
                  <span className="font-bold text-slate-900">{formatCurrency(activeRevision.subtotal)}</span>
                </div>
                {activeRevision.discount_amount > 0 && (
                  <div className="flex justify-between text-emerald-600 font-bold">
                    <span>Discount ({activeRevision.coupon_code}):</span>
                    <span>-{formatCurrency(activeRevision.discount_amount)}</span>
                  </div>
                )}
                <div className="flex justify-between text-slate-600">
                  <span>GST ({activeRevision.tax_rate}%):</span>
                  <span className="font-bold text-slate-900">{formatCurrency(activeRevision.tax_amount)}</span>
                </div>
                <div className="flex justify-between pt-2 border-t border-slate-200 text-sm font-black text-red-600">
                  <span>Grand Total:</span>
                  <span>{formatCurrency(activeRevision.grand_total)}</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Revision Modal */}
      {revisionModalOpen && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-lg w-full max-h-[90vh] flex flex-col p-6 relative overflow-hidden">
            <button onClick={() => setRevisionModalOpen(false)} className="absolute top-5 right-5 text-slate-400 hover:text-slate-700">
              <X className="w-5 h-5" />
            </button>

            <h3 className="text-base font-black text-slate-900 tracking-tight">
              Create New Revision for {quotation.quotation_number}
            </h3>
            <p className="text-xs text-slate-500 mt-1">
              Existing revision {quotation.current_revision_number} will be superseded and preserved immutably.
            </p>

            {revError && (
              <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center space-x-2 text-xs text-red-700">
                <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
                <span>{revError}</span>
              </div>
            )}

            <form onSubmit={handleRevisionSubmit} className="mt-5 space-y-4 text-xs overflow-y-auto flex-1">
              {/* Product Add Bar */}
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-2">
                <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">Add Product Item</label>
                <div className="grid grid-cols-4 gap-2">
                  <div className="col-span-3">
                    <select
                      value={selectedProdId}
                      onChange={(e) => setSelectedProdId(e.target.value)}
                      className="w-full p-2 bg-white border border-slate-200 rounded-lg font-bold text-slate-900"
                    >
                      {availableProducts.map((p) => (
                        <option key={p.id} value={p.id}>
                          [{p.sku}] {p.name}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <input
                      type="number"
                      min={1}
                      value={selectedQty}
                      onChange={(e) => setSelectedQty(parseInt(e.target.value) || 1)}
                      className="w-full p-2 bg-white border border-slate-200 rounded-lg font-black text-center"
                    />
                  </div>
                </div>
                <button
                  type="button"
                  onClick={handleAddRevItem}
                  className="w-full py-2 bg-slate-900 hover:bg-slate-800 text-white font-bold rounded-lg"
                >
                  Add Item
                </button>
              </div>

              {/* Items List */}
              <div className="space-y-2">
                <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                  Revision Items ({revItems.length})
                </label>
                {revItems.map((itm, idx) => {
                  const prod = availableProducts.find((p) => p.id === itm.product_id);
                  return (
                    <div key={idx} className="p-2.5 bg-slate-50 border border-slate-200 rounded-lg flex items-center justify-between">
                      <div>
                        <div className="font-bold text-slate-900">{prod ? prod.name : "Product"}</div>
                        <div className="text-[10px] text-slate-400">Qty: {itm.quantity}</div>
                      </div>
                      <button
                        type="button"
                        onClick={() => handleRemoveRevItem(idx)}
                        className="text-slate-400 hover:text-red-600 p-1"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  );
                })}
              </div>

              <div>
                <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                  Promotional Coupon Code
                </label>
                <input
                  type="text"
                  value={revCoupon}
                  onChange={(e) => setRevCoupon(e.target.value.toUpperCase())}
                  placeholder="e.g. LIVGUARD10"
                  className="mt-1 w-full p-2 bg-slate-50 border border-slate-200 rounded-lg font-mono font-bold"
                />
              </div>

              <div className="flex items-center justify-end space-x-3 pt-4 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setRevisionModalOpen(false)}
                  className="px-4 py-2 border border-slate-200 rounded-lg text-xs font-semibold text-slate-600 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={revLoading || revItems.length === 0}
                  className="px-5 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-xs font-bold shadow-md shadow-red-600/30 disabled:opacity-50"
                >
                  {revLoading ? "Creating..." : "Save Revision"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
