"use client";

import { useEffect, useState } from "react";
import {
  X,
  Search,
  RotateCcw,
  Clock,
  User,
  Phone,
  Mail,
  MapPin,
  FileText,
  AlertCircle,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Loader2,
  Package,
  Layers,
  ArrowRight,
  Tag,
} from "lucide-react";
import { api } from "@/lib/api";
import { formatCurrency, formatDateTime } from "@/lib/utils";

export interface CustomerHistoryItemProduct {
  product_id?: string;
  sku: string;
  product_name: string;
  quantity: number;
  unit_price: number;
  total_price: number;
  current_catalog_price?: number | null;
  is_active: boolean;
}

export interface CustomerQuotationHistoryItem {
  id: string;
  quotation_number: string;
  revision_number: number;
  created_at: string;
  valid_until?: string | null;
  status: string;
  subtotal: number;
  discount_amount: number;
  tax_amount: number;
  grand_total: number;
  coupon_code?: string | null;
  agent_id: string;
  agent_name: string;
  is_own_quotation: boolean;
  items: CustomerHistoryItemProduct[];
}

export interface CustomerQuotationHistoryResponse {
  customer_id: string;
  customer_name: string;
  normalized_mobile: string;
  mobile_display: string;
  email?: string | null;
  address?: string | null;
  quotations: CustomerQuotationHistoryItem[];
  total: number;
  page: number;
  limit: number;
}

export interface QuotationReuseResult {
  message: string;
  new_quotation_id: string;
  source_quotation_id: string;
  source_quotation_number: string;
  customer_name: string;
  customer_mobile: string;
  items_count: number;
  subtotal: number;
  discount_amount: number;
  tax_amount: number;
  grand_total: number;
  coupon_applied?: string | null;
  coupon_warning?: string | null;
  price_updated_notice: string;
  items?: { product_id: string; quantity: number }[];
}

interface Props {
  customerId: string | null;
  customerMobile?: string;
  customerName?: string;
  isOpen: boolean;
  onClose: () => void;
  onReuseQuotation?: (result: QuotationReuseResult, sourceQuote: CustomerQuotationHistoryItem) => void;
}

export function CustomerQuotationHistoryModal({
  customerId,
  customerMobile,
  customerName,
  isOpen,
  onClose,
  onReuseQuotation,
}: Props) {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<CustomerQuotationHistoryResponse | null>(null);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [reusingId, setReusingId] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [reusedSuccessMsg, setReusedSuccessMsg] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && customerId) {
      setPage(1);
      setErrorMsg(null);
      setReusedSuccessMsg(null);
      fetchHistory(customerId, 1, search);
    }
  }, [isOpen, customerId]);

  const fetchHistory = async (cId: string, pageNum: number, searchStr: string) => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const q = searchStr.trim() ? `&search=${encodeURIComponent(searchStr.trim())}` : "";
      const res = await api.get<CustomerQuotationHistoryResponse>(
        `/customers/${cId}/quotations?page=${pageNum}&limit=10${q}`
      );
      setData(res);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to load quotation history.");
    } finally {
      setLoading(false);
    }
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (customerId) {
      setPage(1);
      fetchHistory(customerId, 1, search);
    }
  };

  const handlePageChange = (newPage: number) => {
    if (!customerId) return;
    setPage(newPage);
    fetchHistory(customerId, newPage, search);
  };

  const handleReuse = async (quote: CustomerQuotationHistoryItem) => {
    setReusingId(quote.id);
    setErrorMsg(null);
    try {
      const res = await api.post<QuotationReuseResult>(`/agent/quotations/${quote.id}/reuse`);
      setReusedSuccessMsg(
        `${res.message} (${res.price_updated_notice})` +
          (res.coupon_warning ? ` ⚠️ ${res.coupon_warning}` : "")
      );

      if (onReuseQuotation) {
        onReuseQuotation(res, quote);
      }
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to reuse quotation.");
    } finally {
      setReusingId(null);
    }
  };

  if (!isOpen) return null;

  const totalPages = data ? Math.ceil(data.total / data.limit) : 1;

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "DRAFT":
        return <span className="px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 font-bold text-[10px]">Draft</span>;
      case "ISSUED":
        return <span className="px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 font-bold text-[10px] border border-blue-200">Issued</span>;
      case "PAYMENT_PENDING":
        return <span className="px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 font-bold text-[10px] border border-amber-200">Payment In Review</span>;
      case "PAYMENT_VERIFIED":
        return <span className="px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 font-bold text-[10px] border border-emerald-200">Payment Verified</span>;
      case "ORDER_CONFIRMED":
        return <span className="px-2 py-0.5 rounded-full bg-purple-50 text-purple-700 font-bold text-[10px] border border-purple-200">Order Confirmed</span>;
      case "CANCELLED":
        return <span className="px-2 py-0.5 rounded-full bg-red-50 text-red-700 font-bold text-[10px]">Cancelled</span>;
      default:
        return <span className="px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 font-bold text-[10px]">{status}</span>;
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
      <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between shrink-0">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-red-600/10 border border-red-600/20 text-red-600 flex items-center justify-center font-bold">
              <Clock className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h2 className="text-base font-black text-slate-900">Customer Quotation History</h2>
                {data && (
                  <span className="px-2 py-0.5 bg-red-100 text-red-800 rounded-full text-[10px] font-bold">
                    {data.total} Quotation{data.total === 1 ? "" : "s"}
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-500 mt-0.5 flex items-center space-x-3">
                <span className="font-semibold text-slate-800">
                  {data?.customer_name || customerName || "Customer"}
                </span>
                <span>&bull;</span>
                <span className="font-mono text-slate-600">
                  {data?.mobile_display || customerMobile || ""}
                </span>
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-200 flex items-center justify-center transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Alerts */}
        {errorMsg && (
          <div className="px-6 py-3 bg-red-50 border-b border-red-200 text-red-700 text-xs font-semibold flex items-center space-x-2 shrink-0">
            <AlertCircle className="w-4 h-4 shrink-0 text-red-600" />
            <span>{errorMsg}</span>
          </div>
        )}

        {reusedSuccessMsg && (
          <div className="px-6 py-3 bg-emerald-50 border-b border-emerald-200 text-emerald-800 text-xs font-semibold flex items-center space-x-2 shrink-0">
            <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600" />
            <span>{reusedSuccessMsg}</span>
          </div>
        )}

        {/* Search Bar */}
        <div className="p-4 border-b border-slate-100 bg-white shrink-0">
          <form onSubmit={handleSearchSubmit} className="flex gap-2">
            <div className="relative flex-1">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search by quotation number (e.g. LG/26/0001)..."
                className="w-full pl-9 pr-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500 font-medium"
              />
            </div>
            <button
              type="submit"
              className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-bold transition shadow-xs"
            >
              Search
            </button>
          </form>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {loading && (
            <div className="py-16 text-center space-y-3">
              <Loader2 className="w-8 h-8 animate-spin text-red-600 mx-auto" />
              <p className="text-xs text-slate-500 font-medium">Retrieving customer quotation archive...</p>
            </div>
          )}

          {!loading && (!data || data.quotations.length === 0) && (
            <div className="py-16 text-center border-2 border-dashed border-slate-200 rounded-2xl space-y-3">
              <FileText className="w-10 h-10 text-slate-300 mx-auto" />
              <p className="text-xs font-bold text-slate-700">No previous quotations found</p>
              <p className="text-[11px] text-slate-400 max-w-sm mx-auto">
                No past quotations match your search criteria or this customer does not have any saved quotations yet.
              </p>
            </div>
          )}

          {!loading &&
            data &&
            data.quotations.map((quote) => {
              const isReusing = reusingId === quote.id;
              const hasDeactivatedProduct = quote.items.some((itm) => !itm.is_active);

              return (
                <div
                  key={quote.id}
                  className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs hover:border-slate-300 transition space-y-3"
                >
                  {/* Top Bar: Quotation #, Status, Date, Agent */}
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-2.5">
                    <div className="flex items-center space-x-2">
                      <span className="font-mono font-black text-sm text-slate-900">
                        {quote.quotation_number}
                      </span>
                      {getStatusBadge(quote.status)}
                      <span className="text-[10px] text-slate-400">
                        Rev. {quote.revision_number}
                      </span>
                      {quote.coupon_code && (
                        <span className="inline-flex items-center space-x-1 px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700 text-[10px] font-bold border border-emerald-200">
                          <Tag className="w-2.5 h-2.5" />
                          <span>{quote.coupon_code}</span>
                        </span>
                      )}
                    </div>

                    <div className="flex items-center space-x-3 text-[11px] text-slate-500">
                      <span>Created {formatDateTime(quote.created_at)}</span>
                      <span>&bull;</span>
                      <span
                        className={`font-medium ${
                          quote.is_own_quotation ? "text-slate-700 font-semibold" : "text-amber-700 font-semibold"
                        }`}
                      >
                        {quote.is_own_quotation ? "By You" : `By ${quote.agent_name}`}
                      </span>
                    </div>
                  </div>

                  {/* Line Items List */}
                  <div className="bg-slate-50/70 rounded-lg p-3 space-y-1.5 text-xs">
                    <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">
                      Line Items ({quote.items.length})
                    </div>
                    {quote.items.map((item, idx) => {
                      const priceChanged =
                        item.current_catalog_price !== null &&
                        item.current_catalog_price !== undefined &&
                        Math.abs(item.current_catalog_price - item.unit_price) > 0.01;

                      return (
                        <div
                          key={idx}
                          className="flex items-center justify-between text-[11px] text-slate-700 py-0.5"
                        >
                          <div className="flex items-center space-x-2 truncate">
                            <span className="font-mono font-bold text-slate-900 bg-white border border-slate-200 px-1.5 py-0.2 rounded text-[10px]">
                              {item.sku}
                            </span>
                            <span className="truncate">{item.product_name}</span>
                            <span className="text-slate-400">&times; {item.quantity}</span>

                            {!item.is_active && (
                              <span className="px-1.5 py-0.2 rounded bg-red-100 text-red-700 text-[9px] font-bold">
                                Discontinued
                              </span>
                            )}

                            {item.is_active && priceChanged && (
                              <span className="px-1.5 py-0.2 rounded bg-amber-100 text-amber-800 text-[9px] font-semibold">
                                New Catalog: {formatCurrency(item.current_catalog_price!)}
                              </span>
                            )}
                          </div>

                          <div className="font-semibold text-slate-900 ml-2 shrink-0">
                            {formatCurrency(item.total_price)}
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  {/* Bottom Bar: Financial Totals & Reuse Action */}
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-1">
                    <div className="flex items-center space-x-4 text-xs">
                      <div>
                        <span className="text-slate-400 text-[10px] uppercase font-bold block">Subtotal</span>
                        <span className="font-semibold text-slate-700">{formatCurrency(quote.subtotal)}</span>
                      </div>
                      {quote.discount_amount > 0 && (
                        <div>
                          <span className="text-slate-400 text-[10px] uppercase font-bold block">Discount</span>
                          <span className="font-semibold text-emerald-600">
                            -{formatCurrency(quote.discount_amount)}
                          </span>
                        </div>
                      )}
                      <div>
                        <span className="text-slate-400 text-[10px] uppercase font-bold block">GST</span>
                        <span className="font-semibold text-slate-700">{formatCurrency(quote.tax_amount)}</span>
                      </div>
                      <div className="border-l border-slate-200 pl-4">
                        <span className="text-slate-400 text-[10px] uppercase font-bold block">Grand Total</span>
                        <span className="font-black text-slate-900 text-sm">
                          {formatCurrency(quote.grand_total)}
                        </span>
                      </div>
                    </div>

                    <button
                      type="button"
                      disabled={isReusing}
                      onClick={() => handleReuse(quote)}
                      className="px-4 py-2 bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white rounded-lg text-xs font-bold transition flex items-center justify-center space-x-1.5 shadow-sm shadow-red-600/20 shrink-0"
                    >
                      {isReusing ? (
                        <>
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          <span>Revalidating & Reusing...</span>
                        </>
                      ) : (
                        <>
                          <RotateCcw className="w-3.5 h-3.5" />
                          <span>Reuse Quotation</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>
              );
            })}
        </div>

        {/* Footer / Pagination */}
        {data && totalPages > 1 && (
          <div className="px-6 py-3 border-t border-slate-200 bg-slate-50 flex items-center justify-between shrink-0 text-xs">
            <span className="text-slate-500 font-medium">
              Showing page {data.page} of {totalPages} ({data.total} total)
            </span>
            <div className="flex items-center space-x-2">
              <button
                disabled={page <= 1 || loading}
                onClick={() => handlePageChange(page - 1)}
                className="px-2.5 py-1.5 bg-white border border-slate-200 rounded-lg text-slate-700 hover:bg-slate-100 disabled:opacity-40 font-semibold flex items-center space-x-1"
              >
                <ChevronLeft className="w-3.5 h-3.5" />
                <span>Prev</span>
              </button>
              <button
                disabled={page >= totalPages || loading}
                onClick={() => handlePageChange(page + 1)}
                className="px-2.5 py-1.5 bg-white border border-slate-200 rounded-lg text-slate-700 hover:bg-slate-100 disabled:opacity-40 font-semibold flex items-center space-x-1"
              >
                <span>Next</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
