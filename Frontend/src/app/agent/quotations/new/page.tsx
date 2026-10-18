"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  FilePlus2,
  Search,
  Plus,
  Trash2,
  Ticket,
  CheckCircle2,
  AlertCircle,
  FileText,
  Save,
  Send,
  Loader2,
  Eye,
  Package,
  ShieldCheck,
  Clock,
  Zap,
  Settings,
  UserCheck,
  History,
  RotateCcw,
  Sparkles,
  X,
} from "lucide-react";
import { api } from "@/lib/api";
import { formatCurrency, amountToWordsINR, formatDateTime } from "@/lib/utils";
import { SkuAutocomplete, SearchProduct } from "@/components/SkuAutocomplete";
import {
  getProductCategoryImage,
  getProductCategoryLabel,
} from "@/lib/productCategories";
import {
  CustomerQuotationHistoryModal,
  CustomerQuotationHistoryItem,
  QuotationReuseResult,
} from "@/components/agent/CustomerQuotationHistoryModal";

interface SelectedItem {
  product_id: string;
  sku: string;
  product_name: string;
  category?: string;
  category_display?: string;
  description: string;
  image_url?: string | null;
  unit_price: number;
  quantity: number;
  total_price: number;
}

interface PreviewCalculation {
  customer_name: string;
  customer_mobile: string;
  items: SelectedItem[];
  subtotal: number;
  discount_amount: number;
  coupon_code: string | null;
  tax_rate: number;
  tax_amount: number;
  grand_total: number;
}

export default function NewQuotationPage() {
  const router = useRouter();

  // Customer Form
  const [customerName, setCustomerName] = useState("");
  const [customerMobile, setCustomerMobile] = useState("");
  const [customerEmail, setCustomerEmail] = useState("");
  const [customerAddress, setCustomerAddress] = useState("");

  // Customer Lookup & History State
  const [lookupResult, setLookupResult] = useState<any | null>(null);
  const [lookupLoading, setLookupLoading] = useState(false);
  const [dismissedReturningBanner, setDismissedReturningBanner] = useState(false);
  const [historyModalOpen, setHistoryModalOpen] = useState(false);
  const [selectedCustomerId, setSelectedCustomerId] = useState<string | null>(null);
  const [sourceQuotationId, setSourceQuotationId] = useState<string | null>(null);
  const [reusedBanner, setReusedBanner] = useState<{
    sourceQuoteNumber: string;
    notice: string;
    warning?: string | null;
  } | null>(null);

  // Debounced Returning Customer Lookup by Mobile
  useEffect(() => {
    const rawDigits = customerMobile.replace(/[^0-9]/g, "");
    if (rawDigits.length < 10) {
      setLookupResult(null);
      setDismissedReturningBanner(false);
      return;
    }

    const timer = setTimeout(async () => {
      setLookupLoading(true);
      try {
        const res = await api.get<any>(
          `/customers/lookup?mobile=${encodeURIComponent(customerMobile.trim())}`
        );
        if (res.found) {
          setLookupResult(res);
          setSelectedCustomerId(res.customer.id);
          setDismissedReturningBanner(false);
        } else {
          setLookupResult(null);
        }
      } catch {
        // silent catch on background lookup
      } finally {
        setLookupLoading(false);
      }
    }, 450);

    return () => clearTimeout(timer);
  }, [customerMobile]);

  const handleUseExistingCustomer = () => {
    if (!lookupResult?.customer) return;
    setCustomerName(lookupResult.customer.name);
    if (lookupResult.customer.email) setCustomerEmail(lookupResult.customer.email);
    if (lookupResult.customer.address) setCustomerAddress(lookupResult.customer.address);
    setSelectedCustomerId(lookupResult.customer.id);
    setDismissedReturningBanner(true);
  };

  const handleOpenHistoryModal = () => {
    setHistoryModalOpen(true);
  };

  const handleDismissReturningBanner = () => {
    setDismissedReturningBanner(true);
  };

  const handleQuotationReused = (
    result: QuotationReuseResult,
    sourceQuote: CustomerQuotationHistoryItem
  ) => {
    setCustomerName(result.customer_name);
    setCustomerMobile(result.customer_mobile);
    if (lookupResult?.customer?.email) setCustomerEmail(lookupResult.customer.email);
    if (lookupResult?.customer?.address) setCustomerAddress(lookupResult.customer.address);
    setSourceQuotationId(result.source_quotation_id);

    const activeItems = sourceQuote.items
      .filter((i) => i.is_active && i.product_id)
      .map((i) => ({
        product_id: i.product_id!,
        quantity: i.quantity,
      }));

    if (activeItems.length > 0) {
      setItems(activeItems);
    }

    if (result.coupon_applied) {
      setCouponApplied(result.coupon_applied);
    } else {
      setCouponApplied("");
    }

    setReusedBanner({
      sourceQuoteNumber: result.source_quotation_number,
      notice: result.price_updated_notice,
      warning: result.coupon_warning,
    });

    setHistoryModalOpen(false);
    setDismissedReturningBanner(true);
  };

  // Product Selection via Autocomplete
  const [pendingProduct, setPendingProduct] = useState<SearchProduct | null>(null);
  const [pendingQuantity, setPendingQuantity] = useState(1);

  // Line Items in Quotation
  const [items, setItems] = useState<{ product_id: string; quantity: number }[]>([]);

  // Coupon
  const [couponCode, setCouponCode] = useState("");
  const [couponApplied, setCouponApplied] = useState("");

  // Server-side Preview Calculation
  const [calculation, setCalculation] = useState<PreviewCalculation | null>(null);
  const [calcLoading, setCalcLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [submitLoading, setSubmitLoading] = useState(false);

  // Recalculate preview whenever items or coupon changes
  useEffect(() => {
    if (items.length === 0) {
      setCalculation(null);
      return;
    }

    const runRecalculation = async () => {
      setCalcLoading(true);
      setErrorMsg(null);
      try {
        const preview = await api.post<PreviewCalculation>("/agent/quotations/preview", {
          customer_name: customerName.trim() || "Customer Preview",
          customer_mobile: customerMobile.trim() || "9876543210",
          customer_email: customerEmail.trim() ? customerEmail.trim() : null,
          customer_address: customerAddress.trim() ? customerAddress.trim() : null,
          items,
          coupon_code: couponApplied.trim() ? couponApplied.trim() : null,
        });
        setCalculation(preview);
      } catch (err: any) {
        setErrorMsg(err.message || "Pricing recalculation error");
      } finally {
        setCalcLoading(false);
      }
    };

    runRecalculation();
  }, [items, couponApplied]);

  const handleSelectFromAutocomplete = (product: SearchProduct) => {
    setPendingProduct(product);
    setPendingQuantity(1);
    setErrorMsg(null);
  };

  const handleAddPendingProduct = () => {
    if (!pendingProduct || pendingQuantity <= 0) return;

    const existingIndex = items.findIndex((i) => i.product_id === pendingProduct.id);
    if (existingIndex >= 0) {
      const updated = [...items];
      updated[existingIndex].quantity += pendingQuantity;
      setItems(updated);
    } else {
      setItems([...items, { product_id: pendingProduct.id, quantity: pendingQuantity }]);
    }
    setPendingProduct(null);
    setPendingQuantity(1);
  };

  const handleRemoveItem = (productId: string) => {
    setItems(items.filter((i) => i.product_id !== productId));
  };

  const handleUpdateItemQuantity = (productId: string, qty: number) => {
    if (qty <= 0) {
      handleRemoveItem(productId);
      return;
    }
    setItems(
      items.map((i) => (i.product_id === productId ? { ...i, quantity: qty } : i))
    );
  };

  const handleApplyCoupon = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanCoupon = couponCode.trim().toUpperCase();
    if (!cleanCoupon) return;

    setErrorMsg(null);
    try {
      await api.post("/agent/quotations/preview", {
        customer_name: customerName.trim() || "Customer Preview",
        customer_mobile: customerMobile.trim() || "9876543210",
        customer_email: customerEmail.trim() ? customerEmail.trim() : null,
        customer_address: customerAddress.trim() ? customerAddress.trim() : null,
        items,
        coupon_code: cleanCoupon,
      });
      setCouponApplied(cleanCoupon);
      setCouponCode("");
    } catch (err: any) {
      setErrorMsg(err.message || "Invalid or ineligible coupon code.");
    }
  };

  const handleRemoveCoupon = () => {
    setCouponApplied("");
  };

  const validateMobile = (mobile: string): string | null => {
    const clean = mobile.trim();
    if (!clean) return "Please provide customer mobile contact.";
    if (clean.startsWith("+")) {
      const digits = clean.slice(1).replace(/[^0-9]/g, "");
      if (digits.length < 10 || digits.length > 15) {
        return "International mobile numbers must be between 10 and 15 digits.";
      }
      return null;
    }
    const digits = clean.replace(/[^0-9]/g, "");
    if (digits.length === 10) {
      if (!["6", "7", "8", "9"].includes(digits[0])) {
        return "Indian mobile numbers must begin with 6, 7, 8, or 9 (e.g. 9876543210). For international numbers, please prefix with '+'.";
      }
      return null;
    }
    if (digits.length === 11 && digits.startsWith("0")) {
      if (!["6", "7", "8", "9"].includes(digits[1])) {
        return "Indian mobile numbers must begin with 6, 7, 8, or 9 after leading 0.";
      }
      return null;
    }
    if (digits.length === 12 && digits.startsWith("91")) {
      if (!["6", "7", "8", "9"].includes(digits[2])) {
        return "Indian mobile numbers must begin with 6, 7, 8, or 9 after 91 country code.";
      }
      return null;
    }
    return "Please enter a valid 10-digit mobile number (or prefix with '+' for international numbers).";
  };

  const handleSaveDraft = async () => {
    const cleanName = customerName.trim();
    const cleanMobile = customerMobile.trim();
    if (!cleanName || !cleanMobile) {
      setErrorMsg("Please provide customer name and mobile contact before saving draft.");
      return;
    }
    const mobileErr = validateMobile(cleanMobile);
    if (mobileErr) {
      setErrorMsg(mobileErr);
      return;
    }
    if (items.length === 0) {
      setErrorMsg("Please add at least one product before saving.");
      return;
    }

    setSubmitLoading(true);
    setErrorMsg(null);
    try {
      const res = await api.post<{ message: string; quotation_id: string }>(
        "/agent/quotations/draft",
        {
          customer_name: cleanName,
          customer_mobile: cleanMobile,
          customer_email: customerEmail.trim() ? customerEmail.trim() : null,
          customer_address: customerAddress.trim() ? customerAddress.trim() : null,
          items,
          coupon_code: couponApplied.trim() ? couponApplied.trim() : null,
          source_quotation_id: sourceQuotationId || null,
        }
      );
      router.push(`/agent/quotations/${res.quotation_id}`);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to save draft quotation.");
    } finally {
      setSubmitLoading(false);
    }
  };

  const handleIssueQuotation = async () => {
    const cleanName = customerName.trim();
    const cleanMobile = customerMobile.trim();
    if (!cleanName || !cleanMobile) {
      setErrorMsg("Please provide customer name and mobile contact to issue an official quotation.");
      return;
    }
    const mobileErr = validateMobile(cleanMobile);
    if (mobileErr) {
      setErrorMsg(mobileErr);
      return;
    }
    if (items.length === 0) {
      setErrorMsg("Please add at least one product before issuing.");
      return;
    }

    setSubmitLoading(true);
    setErrorMsg(null);
    try {
      const res = await api.post<{ message: string; quotation_id: string; quotation_number: string }>(
        "/agent/quotations/issue",
        {
          customer_name: cleanName,
          customer_mobile: cleanMobile,
          customer_email: customerEmail.trim() ? customerEmail.trim() : null,
          customer_address: customerAddress.trim() ? customerAddress.trim() : null,
          items,
          coupon_code: couponApplied.trim() ? couponApplied.trim() : null,
          source_quotation_id: sourceQuotationId || null,
        }
      );
      router.push(`/agent/quotations/${res.quotation_id}`);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to issue quotation.");
    } finally {
      setSubmitLoading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-black text-slate-900 tracking-tight">Create Customer Quotation</h1>
        <p className="text-xs text-slate-500 mt-1">
          Searchable SKU lookup, dynamic price recalculation, authorized coupon discount and pixel-perfect Livguard branded preview
        </p>
      </div>

      {reusedBanner && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl space-y-1.5 text-xs text-emerald-900 shadow-xs animate-in fade-in">
          <div className="flex items-center justify-between font-bold text-emerald-800">
            <div className="flex items-center space-x-2">
              <RotateCcw className="w-4 h-4 text-emerald-600 shrink-0" />
              <span>Quotation Reloaded from {reusedBanner.sourceQuoteNumber}</span>
            </div>
            <button
              type="button"
              onClick={() => setReusedBanner(null)}
              className="text-emerald-500 hover:text-emerald-700"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
          <p className="text-emerald-700 font-medium pl-6">{reusedBanner.notice}</p>
          {reusedBanner.warning && (
            <p className="text-amber-800 font-semibold pl-6">⚠️ {reusedBanner.warning}</p>
          )}
        </div>
      )}

      {errorMsg && (
        <div className="p-3.5 bg-red-50 border border-red-200 rounded-xl flex items-center space-x-2.5 text-xs text-red-700 font-semibold shadow-sm">
          <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Form Inputs */}
        <div className="lg:col-span-7 space-y-6">
          {/* Step 1: Customer Details */}
          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-xs font-black uppercase tracking-wider text-slate-800 flex items-center space-x-2">
                <span className="w-5 h-5 rounded-full bg-red-600 text-white flex items-center justify-center text-[10px]">
                  1
                </span>
                <span>Customer Identification</span>
              </h2>

              {(selectedCustomerId || lookupResult?.found) && (
                <button
                  type="button"
                  onClick={handleOpenHistoryModal}
                  className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-lg bg-red-50 hover:bg-red-100 text-red-700 text-xs font-bold border border-red-200 transition"
                >
                  <Clock className="w-3.5 h-3.5" />
                  <span>View Quotation History</span>
                </button>
              )}
            </div>

            {/* Returning Customer Notification Banner */}
            {lookupResult?.found && !dismissedReturningBanner && (
              <div className="p-4 bg-gradient-to-br from-amber-50 to-orange-50/40 border border-amber-200 rounded-xl space-y-3 shadow-xs">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-start space-x-2.5">
                    <div className="w-8 h-8 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-600 flex items-center justify-center shrink-0 mt-0.5">
                      <Sparkles className="w-4 h-4" />
                    </div>
                    <div>
                      <div className="flex items-center space-x-2">
                        <h3 className="text-xs font-black text-slate-900 uppercase tracking-wide">
                          Returning Customer Identified
                        </h3>
                        <span className="px-2 py-0.5 bg-amber-200 text-amber-900 rounded-full text-[10px] font-bold">
                          Existing Profile
                        </span>
                      </div>
                      <p className="text-xs text-slate-600 mt-0.5">
                        Mobile <strong className="font-mono text-slate-900">{lookupResult.mobile_display}</strong> is already registered to <strong className="text-slate-900">{lookupResult.customer.name}</strong>.
                      </p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={handleDismissReturningBanner}
                    className="text-slate-400 hover:text-slate-600 p-1"
                    title="Dismiss notification"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>

                {/* Quotation Stats Summary */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 bg-white/80 backdrop-blur-xs p-2.5 rounded-lg border border-amber-100 text-[11px]">
                  <div>
                    <span className="text-slate-400 text-[10px] uppercase font-bold block">Total Quotes</span>
                    <span className="font-black text-slate-800">{lookupResult.stats?.total_quotations || 0}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 text-[10px] uppercase font-bold block">Latest Quotation</span>
                    <span className="font-mono font-bold text-slate-800 truncate block">
                      {lookupResult.stats?.latest_quotation_number || "None"}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-400 text-[10px] uppercase font-bold block">Status</span>
                    <span className="font-semibold text-slate-700 block">
                      {lookupResult.stats?.latest_quotation_status || "N/A"}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-400 text-[10px] uppercase font-bold block">Last Value</span>
                    <span className="font-bold text-slate-900 block">
                      {lookupResult.stats?.latest_quotation_grand_total
                        ? formatCurrency(lookupResult.stats.latest_quotation_grand_total)
                        : "N/A"}
                    </span>
                  </div>
                </div>

                {!lookupResult.stats?.created_by_same_agent && (
                  <div className="text-[11px] text-amber-800 flex items-center space-x-1 font-medium bg-amber-100/60 px-2.5 py-1 rounded">
                    <span>Originally registered by agent: <strong>{lookupResult.customer.created_by_agent_name || "Another Agent"}</strong></span>
                  </div>
                )}

                {/* 3 Explicit Actions as required */}
                <div className="flex flex-wrap items-center gap-2 pt-1">
                  <button
                    type="button"
                    onClick={handleUseExistingCustomer}
                    className="px-3 py-1.5 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-xs font-bold transition shadow-xs flex items-center space-x-1.5"
                  >
                    <UserCheck className="w-3.5 h-3.5" />
                    <span>Use Existing Customer</span>
                  </button>
                  <button
                    type="button"
                    onClick={handleOpenHistoryModal}
                    className="px-3 py-1.5 bg-white border border-amber-300 hover:bg-amber-50 text-slate-800 rounded-lg text-xs font-bold transition shadow-xs flex items-center space-x-1.5"
                  >
                    <History className="w-3.5 h-3.5 text-amber-600" />
                    <span>View Quotation History ({lookupResult.stats?.total_quotations || 0})</span>
                  </button>
                  <button
                    type="button"
                    onClick={handleDismissReturningBanner}
                    className="px-2.5 py-1.5 text-slate-600 hover:text-slate-900 text-xs font-semibold"
                  >
                    Create New Quotation
                  </button>
                </div>
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div>
                <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                  Customer Full Name *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Rohan Mehra"
                  value={customerName}
                  onChange={(e) => setCustomerName(e.target.value)}
                  className="mt-1 w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg font-bold text-slate-900 focus:ring-2 focus:ring-red-500 focus:bg-white outline-none"
                />
              </div>

              <div>
                <div className="flex items-center justify-between">
                  <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                    Mobile Contact *
                  </label>
                  {lookupLoading && (
                    <span className="text-[10px] text-slate-400 flex items-center space-x-1 font-semibold">
                      <Loader2 className="w-3 h-3 animate-spin text-red-600" />
                      <span>Checking...</span>
                    </span>
                  )}
                  {!lookupLoading && lookupResult?.found && (
                    <span className="text-[10px] text-emerald-600 flex items-center space-x-1 font-bold">
                      <UserCheck className="w-3 h-3" />
                      <span>Returning Customer</span>
                    </span>
                  )}
                </div>
                <input
                  type="tel"
                  required
                  placeholder="e.g. 9876543210 or +91 9876543210"
                  value={customerMobile}
                  onChange={(e) => setCustomerMobile(e.target.value)}
                  className={`mt-1 w-full p-2.5 bg-slate-50 border rounded-lg font-bold text-slate-900 focus:ring-2 focus:bg-white outline-none ${
                    (() => {
                      const raw = customerMobile.trim();
                      if (!raw || raw.startsWith("+")) return false;
                      const digits = raw.replace(/[^0-9]/g, "");
                      if (digits.length >= 10 && !["6", "7", "8", "9"].includes(digits[0])) return true;
                      if (digits.length === 11 && digits.startsWith("0") && !["6", "7", "8", "9"].includes(digits[1])) return true;
                      if (digits.length === 12 && digits.startsWith("91") && !["6", "7", "8", "9"].includes(digits[2])) return true;
                      return false;
                    })()
                      ? "border-amber-400 focus:ring-amber-500 bg-amber-50/30"
                      : "border-slate-200 focus:ring-red-500"
                  }`}
                />
                {(() => {
                  const raw = customerMobile.trim();
                  if (!raw || raw.startsWith("+")) return false;
                  const digits = raw.replace(/[^0-9]/g, "");
                  if (digits.length >= 10 && !["6", "7", "8", "9"].includes(digits[0])) return true;
                  if (digits.length === 11 && digits.startsWith("0") && !["6", "7", "8", "9"].includes(digits[1])) return true;
                  if (digits.length === 12 && digits.startsWith("91") && !["6", "7", "8", "9"].includes(digits[2])) return true;
                  return false;
                })() && (
                  <p className="text-[10px] text-amber-700 font-semibold mt-1">
                    ⚠️ Indian mobile numbers must begin with 6, 7, 8, or 9 (or include &apos;+&apos; for international).
                  </p>
                )}
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div>
                <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                  Email Address (Optional)
                </label>
                <input
                  type="email"
                  placeholder="rohan@example.com"
                  value={customerEmail}
                  onChange={(e) => setCustomerEmail(e.target.value)}
                  className="mt-1 w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:ring-2 focus:ring-red-500 focus:bg-white outline-none"
                />
              </div>

              <div>
                <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                  Delivery / Installation Address
                </label>
                <input
                  type="text"
                  placeholder="B-42, Sector 14, Noida, UP"
                  value={customerAddress}
                  onChange={(e) => setCustomerAddress(e.target.value)}
                  className="mt-1 w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:ring-2 focus:ring-red-500 focus:bg-white outline-none"
                />
              </div>
            </div>
          </div>

          {/* Step 2: SKU Searchable Autocomplete Entry (Mandatory Requirement) */}
          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-4">
            <h2 className="text-xs font-black uppercase tracking-wider text-slate-800 flex items-center space-x-2">
              <span className="w-5 h-5 rounded-full bg-red-600 text-white flex items-center justify-center text-[10px]">
                2
              </span>
              <span>Searchable SKU Product Selector</span>
            </h2>

            <div className="space-y-3">
              <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                Type SKU code or product name to search
              </label>

              {/* Dedicated Autocomplete Component */}
              <SkuAutocomplete
                onSelectProduct={handleSelectFromAutocomplete}
                placeholder="Type SKU or product name (e.g. LG-SET-1, Inverter, Tubular)..."
              />

              {/* Active Selection Staging Card */}
              {pendingProduct && (
                <div className="mt-3 p-4 bg-red-50/50 border-2 border-red-200 rounded-xl flex flex-col sm:flex-row items-center justify-between gap-4">
                  <div className="flex items-center gap-3">
                    <div className="w-14 h-14 bg-white rounded-lg border border-slate-200 p-1 flex items-center justify-center overflow-hidden shrink-0">
                      <img
                        src={getProductCategoryImage(pendingProduct.category, pendingProduct.image_url)}
                        alt={pendingProduct.name}
                        className="w-full h-full object-contain"
                        onError={(e) => {
                          (e.target as HTMLImageElement).src = "/uploads/products/inverter.png";
                        }}
                      />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-[10px] font-black px-1.5 py-0.5 rounded bg-slate-900 text-white">
                          {pendingProduct.sku}
                        </span>
                        <span className="text-[10px] font-bold text-red-600 uppercase bg-red-100/80 px-1.5 py-0.5 rounded">
                          {getProductCategoryLabel(pendingProduct.category)}
                        </span>
                      </div>
                      <div className="font-bold text-xs text-slate-900 mt-1">{pendingProduct.name}</div>
                      <div className="text-[11px] font-extrabold text-red-600 mt-0.5">
                        {formatCurrency(pendingProduct.unit_price)} <span className="text-[9px] text-slate-500 font-normal">unit price</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 w-full sm:w-auto">
                    <div className="flex items-center gap-1.5 bg-white border border-slate-200 rounded-lg p-1">
                      <label className="text-[10px] font-bold text-slate-500 px-1">Qty:</label>
                      <input
                        type="number"
                        min={1}
                        value={pendingQuantity}
                        onChange={(e) => setPendingQuantity(Math.max(1, parseInt(e.target.value) || 1))}
                        className="w-14 p-1.5 font-black text-center text-xs text-slate-900 border-none outline-none"
                      />
                    </div>
                    <button
                      type="button"
                      onClick={handleAddPendingProduct}
                      className="flex-1 sm:flex-none py-2 px-4 bg-red-600 hover:bg-red-700 text-white font-bold text-xs rounded-lg shadow-sm transition flex items-center justify-center gap-1.5"
                    >
                      <Plus className="w-4 h-4" />
                      <span>Add Item</span>
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Line Items Table */}
            <div className="mt-4 pt-4 border-t border-slate-100">
              <div className="flex items-center justify-between mb-2">
                <span className="text-[11px] font-extrabold uppercase text-slate-700 tracking-wider">
                  Quotation Line Items ({items.length})
                </span>
                {items.length > 0 && (
                  <button
                    type="button"
                    onClick={() => setItems([])}
                    className="text-[10px] text-red-600 hover:text-red-700 font-bold"
                  >
                    Clear All
                  </button>
                )}
              </div>

              {items.length === 0 ? (
                <div className="p-6 bg-slate-50 border border-dashed border-slate-200 rounded-xl text-center">
                  <Package className="w-6 h-6 text-slate-400 mx-auto mb-1.5" />
                  <div className="text-xs font-bold text-slate-600">No products added yet</div>
                  <div className="text-[11px] text-slate-400 mt-0.5">
                    Use the SKU search bar above to find and add Livguard batteries, inverters or combo sets.
                  </div>
                </div>
              ) : (
                <div className="border border-slate-200 rounded-xl overflow-hidden divide-y divide-slate-100">
                  {calculation?.items?.map((item, idx) => (
                    <div key={item.product_id} className="p-3 bg-white flex items-center justify-between gap-3 text-xs">
                      <div className="flex items-center gap-3 min-w-0">
                        <span className="w-5 h-5 rounded-full bg-slate-100 text-slate-600 font-mono font-bold text-[10px] flex items-center justify-center shrink-0">
                          {idx + 1}
                        </span>
                        <div className="w-10 h-10 bg-white rounded border border-slate-200 p-0.5 flex items-center justify-center overflow-hidden shrink-0">
                          <img
                            src={getProductCategoryImage(item.category, item.image_url)}
                            alt={item.product_name}
                            className="w-full h-full object-contain"
                            onError={(e) => {
                              (e.target as HTMLImageElement).src = "/uploads/products/inverter.png";
                            }}
                          />
                        </div>
                        <div className="min-w-0">
                          <div className="font-bold text-slate-900 truncate">{item.product_name}</div>
                          <div className="flex items-center gap-2 mt-0.5">
                            <span className="font-mono text-[10px] text-red-600 font-bold">{item.sku}</span>
                            <span className="text-[10px] text-slate-400">@ {formatCurrency(item.unit_price)}</span>
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center gap-3 shrink-0">
                        <div className="flex items-center gap-1 border border-slate-200 rounded-lg p-0.5 bg-slate-50">
                          <button
                            type="button"
                            onClick={() => handleUpdateItemQuantity(item.product_id, item.quantity - 1)}
                            className="w-6 h-6 flex items-center justify-center text-slate-600 hover:bg-white rounded font-bold text-xs"
                          >
                            -
                          </button>
                          <span className="w-7 text-center font-black text-slate-900 text-xs">
                            {item.quantity}
                          </span>
                          <button
                            type="button"
                            onClick={() => handleUpdateItemQuantity(item.product_id, item.quantity + 1)}
                            className="w-6 h-6 flex items-center justify-center text-slate-600 hover:bg-white rounded font-bold text-xs"
                          >
                            +
                          </button>
                        </div>

                        <div className="w-20 text-right font-black text-slate-900 text-xs">
                          {formatCurrency(item.total_price)}
                        </div>

                        <button
                          type="button"
                          onClick={() => handleRemoveItem(item.product_id)}
                          className="p-1.5 text-slate-400 hover:text-red-600 transition"
                          title="Remove item"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Step 3: Promotional Coupon Code */}
          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-4">
            <h2 className="text-xs font-black uppercase tracking-wider text-slate-800 flex items-center space-x-2">
              <span className="w-5 h-5 rounded-full bg-red-600 text-white flex items-center justify-center text-[10px]">
                3
              </span>
              <span>Promotional Coupon Code</span>
            </h2>

            {couponApplied ? (
              <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl flex items-center justify-between text-xs">
                <div className="flex items-center space-x-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                  <span className="font-bold text-emerald-900">
                    Coupon <span className="font-mono">{couponApplied}</span> Applied
                  </span>
                </div>
                <button
                  type="button"
                  onClick={handleRemoveCoupon}
                  className="text-xs font-bold text-red-600 hover:text-red-700"
                >
                  Remove
                </button>
              </div>
            ) : (
              <form onSubmit={handleApplyCoupon} className="flex gap-2">
                <input
                  type="text"
                  placeholder="e.g. LIVGUARD10"
                  value={couponCode}
                  onChange={(e) => setCouponCode(e.target.value.toUpperCase())}
                  className="flex-1 p-2.5 bg-slate-50 border border-slate-200 rounded-lg font-mono font-bold text-xs focus:ring-2 focus:ring-red-500 focus:bg-white outline-none"
                />
                <button
                  type="submit"
                  disabled={!couponCode.trim() || items.length === 0}
                  className="px-4 py-2.5 bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs rounded-lg transition disabled:opacity-40"
                >
                  Apply
                </button>
              </form>
            )}
          </div>
        </div>

        {/* Right Column: Branded Quotation Live Preview (Exact Quotation Format Match) */}
        <div className="lg:col-span-5 space-y-4">
          <div className="bg-white rounded-2xl border-2 border-slate-300 shadow-xl overflow-hidden sticky top-20">
            {/* Live Preview Header Bar */}
            <div className="bg-slate-900 text-white p-3 flex items-center justify-between text-xs font-bold">
              <span className="flex items-center space-x-1.5">
                <Eye className="w-4 h-4 text-red-500" />
                <span>Live Quotation Preview</span>
              </span>
              {calcLoading && <span className="text-[10px] text-red-400 animate-pulse">Calculating...</span>}
            </div>

            {/* Document Body */}
            <div className="p-4 sm:p-5 space-y-3.5 text-xs bg-white text-slate-900">
              {/* Header: 1. Banner, 2. Logo + QUOTATION Heading Image */}
              <div className="space-y-1.5 border-b border-slate-200 pb-2">
                <img
                  src="/assets/Banner.png"
                  alt="Livguard Banner"
                  className="w-full h-auto rounded object-contain block"
                />
                <img
                  src="/assets/LogoQuotation.png"
                  alt="Livguard Quotation"
                  className="w-full h-auto object-contain block"
                />
              </div>

              {/* Customer & Quotation Details (Combined Single Panel) */}
              <div className="bg-slate-50 p-2.5 rounded-xl border border-slate-200">
                <div className="grid grid-cols-2 gap-3 text-[10.5px]">
                  {/* Left: Customer Details */}
                  <div className="space-y-1">
                    <div className="text-[10px] font-black text-red-600 uppercase">Customer Details</div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Name:</span>
                      <span className="font-bold text-slate-900 truncate max-w-[90px]">
                        {customerName || "—"}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Contact:</span>
                      <span className="font-semibold text-slate-800">{customerMobile || "—"}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Address:</span>
                      <span className="text-slate-700 truncate max-w-[90px]">{customerAddress || "—"}</span>
                    </div>
                  </div>

                  {/* Right: Quotation Details */}
                  <div className="space-y-1 pl-3 border-l border-slate-200">
                    <div className="text-[10px] font-black text-slate-700 uppercase">Quotation Details</div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Quote No:</span>
                      <span className="font-mono font-bold text-red-600">LGQ/2026/001</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Date:</span>
                      <span className="font-semibold text-slate-800">Today</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">No. of Products:</span>
                      <span className="font-bold text-slate-900">
                        {items.reduce((sum, itm) => sum + itm.quantity, 0)}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Exact 7-Column Products Table */}
              <div className="border border-slate-200 rounded-lg overflow-hidden">
                <table className="w-full text-left text-[9.5px]">
                  <thead className="bg-slate-900 text-white uppercase text-[8px] font-bold">
                    <tr>
                      <th className="py-2 px-1 text-center w-6">S.No.</th>
                      <th className="py-2 px-1 text-center w-10">Product</th>
                      <th className="py-2 px-1.5 text-center">SKU / Model No.</th>
                      <th className="py-2 px-2">Description</th>
                      <th className="py-2 px-1 text-center w-8">Qty.</th>
                      <th className="py-2 px-1.5 text-right">Unit Price (₹)</th>
                      <th className="py-2 px-1.5 text-right">Total Price (₹)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {calculation?.items && calculation.items.length > 0 ? (
                      calculation.items.map((itm, idx) => (
                        <tr key={itm.product_id} className="hover:bg-slate-50/50">
                          <td className="py-2 px-1 text-center font-bold text-slate-500">{idx + 1}</td>
                          <td className="py-2 px-1 text-center">
                            <div className="w-8 h-8 mx-auto bg-white rounded border border-slate-200 p-0.5 flex items-center justify-center overflow-hidden shrink-0">
                              <img
                                src={getProductCategoryImage(itm.category, itm.image_url)}
                                alt={itm.product_name}
                                className="w-full h-full object-contain"
                                onError={(e) => {
                                  (e.target as HTMLImageElement).src = "/uploads/products/inverter.png";
                               }}
                              />
                            </div>
                          </td>
                          <td className="py-2 px-1.5 text-center font-mono text-[9px] text-red-600 font-bold whitespace-nowrap">
                            {itm.sku}
                          </td>
                          <td className="py-2 px-2">
                            <div className="font-bold text-slate-900 leading-tight">{itm.product_name}</div>
                            {itm.description && (
                              <div className="text-[8px] text-slate-400 line-clamp-1 mt-0.5">
                                {itm.description.replace(/\n/g, " • ")}
                              </div>
                            )}
                          </td>
                          <td className="py-2 px-1 text-center font-bold text-slate-800">{itm.quantity}</td>
                          <td className="py-2 px-1.5 text-right text-slate-700 whitespace-nowrap">
                            {formatCurrency(itm.unit_price)}
                          </td>
                          <td className="py-2 px-1.5 text-right font-black text-slate-900 whitespace-nowrap">
                            {formatCurrency(itm.total_price)}
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={7} className="py-6 text-center text-slate-400 text-xs">
                          Search and add items to see live preview
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>

              {/* Trust Badges Row */}
              <div className="grid grid-cols-4 gap-1 py-1 text-center border-t border-b border-slate-100">
                <div className="flex flex-col items-center">
                  <ShieldCheck className="w-3.5 h-3.5 text-red-600" />
                  <span className="text-[8px] font-bold text-slate-700 mt-0.5">Reliable</span>
                </div>
                <div className="flex flex-col items-center">
                  <Clock className="w-3.5 h-3.5 text-red-600" />
                  <span className="text-[8px] font-bold text-slate-700 mt-0.5">Backup</span>
                </div>
                <div className="flex flex-col items-center">
                  <Zap className="w-3.5 h-3.5 text-red-600" />
                  <span className="text-[8px] font-bold text-slate-700 mt-0.5">Fast Charge</span>
                </div>
                <div className="flex flex-col items-center">
                  <Settings className="w-3.5 h-3.5 text-red-600" />
                  <span className="text-[8px] font-bold text-slate-700 mt-0.5">Low Maint.</span>
                </div>
              </div>

              {/* Financial Totals Box */}
              {calculation && (
                <div className="space-y-1 pt-1 text-xs">
                  <div className="flex justify-between text-slate-600">
                    <span>Subtotal:</span>
                    <span className="font-bold text-slate-900">{formatCurrency(calculation.subtotal)}</span>
                  </div>
                  {calculation.discount_amount > 0 && (
                    <div className="flex justify-between text-emerald-600 font-bold">
                      <span>Discount ({calculation.coupon_code}):</span>
                      <span>-{formatCurrency(calculation.discount_amount)}</span>
                    </div>
                  )}
                  <div className="flex justify-between text-slate-600">
                    <span>GST ({calculation.tax_rate}%):</span>
                    <span className="font-bold text-slate-900">{formatCurrency(calculation.tax_amount)}</span>
                  </div>
                  <div className="flex justify-between p-2 rounded-lg bg-red-600 text-white font-black text-sm shadow-sm">
                    <span>Grand Total (₹):</span>
                    <span>{formatCurrency(calculation.grand_total)}</span>
                  </div>
                  {/* Amount in Words */}
                  <div className="bg-slate-50 border border-slate-200 border-l-4 border-l-red-600 rounded-lg p-2 text-[10px] mt-2">
                    <span className="font-extrabold text-slate-900">Amount in Words: </span>
                    <span className="font-bold text-red-700 italic">{amountToWordsINR(calculation.grand_total)}</span>
                  </div>
                </div>
              )}
            </div>

            {/* Action Buttons */}
            <div className="p-4 bg-slate-50 border-t border-slate-200 space-y-2">
              <button
                type="button"
                onClick={handleIssueQuotation}
                disabled={submitLoading || items.length === 0}
                className="w-full py-3 bg-red-600 hover:bg-red-700 text-white font-black text-xs uppercase tracking-wider rounded-xl shadow-lg shadow-red-600/30 transition flex items-center justify-center space-x-2 disabled:opacity-50 cursor-pointer"
              >
                {submitLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Issuing Quotation...</span>
                  </>
                ) : (
                  <>
                    <Send className="w-4 h-4" />
                    <span>Issue Official Quotation</span>
                  </>
                )}
              </button>

              <button
                type="button"
                onClick={handleSaveDraft}
                disabled={submitLoading || items.length === 0}
                className="w-full py-2.5 bg-white border border-slate-200 hover:bg-slate-100 text-slate-700 font-bold text-xs rounded-xl transition flex items-center justify-center space-x-1.5 disabled:opacity-50 cursor-pointer"
              >
                <Save className="w-3.5 h-3.5" />
                <span>Save as Draft</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Customer Quotation History Modal */}
      <CustomerQuotationHistoryModal
        isOpen={historyModalOpen}
        onClose={() => setHistoryModalOpen(false)}
        customerId={selectedCustomerId || lookupResult?.customer?.id || null}
        customerName={lookupResult?.customer?.name || customerName}
        customerMobile={lookupResult?.mobile_display || customerMobile}
        onReuseQuotation={handleQuotationReused}
      />
    </div>
  );
}
