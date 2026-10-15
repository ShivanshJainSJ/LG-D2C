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
  ArrowRight,
} from "lucide-react";
import { api } from "@/lib/api";
import { formatCurrency } from "@/lib/utils";

interface ActiveProduct {
  id: string;
  sku: string;
  name: string;
  brand: string;
  category: string;
  description: string;
  unit_price: number;
}

interface SelectedItem {
  product_id: string;
  sku: string;
  product_name: string;
  description: string;
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

  // Products from Master
  const [availableProducts, setAvailableProducts] = useState<ActiveProduct[]>([]);
  const [productSearch, setProductSearch] = useState("");

  // Customer Form
  const [customerName, setCustomerName] = useState("");
  const [customerMobile, setCustomerMobile] = useState("");
  const [customerEmail, setCustomerEmail] = useState("");
  const [customerAddress, setCustomerAddress] = useState("");

  // Line Items
  const [items, setItems] = useState<{ product_id: string; quantity: number }[]>([]);
  const [selectedProductId, setSelectedProductId] = useState("");
  const [inputQuantity, setInputQuantity] = useState(1);

  // Coupon
  const [couponCode, setCouponCode] = useState("");
  const [couponApplied, setCouponApplied] = useState("");

  // Server-side Preview Calculation
  const [calculation, setCalculation] = useState<PreviewCalculation | null>(null);
  const [calcLoading, setCalcLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [submitLoading, setSubmitLoading] = useState(false);

  useEffect(() => {
    const fetchCatalog = async () => {
      try {
        const prods = await api.get<ActiveProduct[]>("/agent/products");
        setAvailableProducts(prods);
        if (prods.length > 0) {
          setSelectedProductId(prods[0].id);
        }
      } catch (err) {
        console.error("Failed to load products:", err);
      }
    };
    fetchCatalog();
  }, []);

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
          customer_name: customerName || "Customer Preview",
          customer_mobile: customerMobile || "9876543210",
          customer_email: customerEmail || undefined,
          customer_address: customerAddress || undefined,
          items,
          coupon_code: couponApplied || undefined,
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

  const handleAddItem = () => {
    if (!selectedProductId || inputQuantity <= 0) return;

    const existingIndex = items.findIndex((i) => i.product_id === selectedProductId);
    if (existingIndex >= 0) {
      const updated = [...items];
      updated[existingIndex].quantity += inputQuantity;
      setItems(updated);
    } else {
      setItems([...items, { product_id: selectedProductId, quantity: inputQuantity }]);
    }
    setInputQuantity(1);
  };

  const handleRemoveItem = (index: number) => {
    const updated = items.filter((_, idx) => idx !== index);
    setItems(updated);
  };

  const handleApplyCoupon = (e: React.FormEvent) => {
    e.preventDefault();
    if (!couponCode.trim()) return;
    setCouponApplied(couponCode.trim().toUpperCase());
  };

  const handleRemoveCoupon = () => {
    setCouponCode("");
    setCouponApplied("");
  };

  const handleSaveDraft = async () => {
    if (!customerName || !customerMobile || items.length === 0) {
      setErrorMsg("Customer name, mobile number and at least one line item are required.");
      return;
    }
    setSubmitLoading(true);
    setErrorMsg(null);
    try {
      const res = await api.post<{ quotation_id: string }>("/agent/quotations/draft", {
        customer_name: customerName,
        customer_mobile: customerMobile,
        customer_email: customerEmail || null,
        customer_address: customerAddress || null,
        items,
        coupon_code: couponApplied || null,
      });
      router.push(`/agent/quotations/${res.quotation_id}`);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to save draft.");
    } finally {
      setSubmitLoading(false);
    }
  };

  const handleIssueQuotation = async () => {
    if (!customerName || !customerMobile || items.length === 0) {
      setErrorMsg("Customer name, mobile number and at least one line item are required.");
      return;
    }
    setSubmitLoading(true);
    setErrorMsg(null);
    try {
      const res = await api.post<{ quotation_id: string; quotation_number: string }>(
        "/agent/quotations/issue",
        {
          customer_name: customerName,
          customer_mobile: customerMobile,
          customer_email: customerEmail || null,
          customer_address: customerAddress || null,
          items,
          coupon_code: couponApplied || null,
        }
      );
      router.push(`/agent/quotations/${res.quotation_id}`);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to issue quotation.");
    } finally {
      setSubmitLoading(false);
    }
  };

  const filteredProducts = availableProducts.filter(
    (p) =>
      p.sku.toLowerCase().includes(productSearch.toLowerCase()) ||
      p.name.toLowerCase().includes(productSearch.toLowerCase())
  );

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-black text-slate-900 tracking-tight">Create Customer Quotation</h1>
        <p className="text-xs text-slate-500 mt-1">
          SKU lookup, dynamic price recalculation, authorized coupon discount and instant Livguard branded preview
        </p>
      </div>

      {errorMsg && (
        <div className="p-3.5 bg-red-50 border border-red-200 rounded-xl flex items-center space-x-2.5 text-xs text-red-700 font-semibold">
          <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Input Forms */}
        <div className="lg:col-span-7 space-y-6">
          {/* Step 1: Customer Details */}
          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-4">
            <h2 className="text-xs font-black uppercase tracking-wider text-slate-800 flex items-center space-x-2">
              <span className="w-5 h-5 rounded-full bg-red-600 text-white flex items-center justify-center text-[10px]">
                1
              </span>
              <span>Customer Identification</span>
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div>
                <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                  Customer Full Name *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Ramesh Kumar"
                  value={customerName}
                  onChange={(e) => setCustomerName(e.target.value)}
                  className="mt-1 w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg font-bold text-slate-900 focus:ring-2 focus:ring-red-500 focus:bg-white"
                />
              </div>

              <div>
                <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                  Mobile Contact *
                </label>
                <input
                  type="tel"
                  required
                  placeholder="e.g. 9876543210"
                  value={customerMobile}
                  onChange={(e) => setCustomerMobile(e.target.value)}
                  className="mt-1 w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg font-bold text-slate-900 focus:ring-2 focus:ring-red-500 focus:bg-white"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div>
                <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                  Email Address (Optional)
                </label>
                <input
                  type="email"
                  placeholder="ramesh@example.com"
                  value={customerEmail}
                  onChange={(e) => setCustomerEmail(e.target.value)}
                  className="mt-1 w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:ring-2 focus:ring-red-500 focus:bg-white"
                />
              </div>

              <div>
                <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                  Delivery / Installation Address
                </label>
                <input
                  type="text"
                  placeholder="Sector 14, Gurugram, Haryana"
                  value={customerAddress}
                  onChange={(e) => setCustomerAddress(e.target.value)}
                  className="mt-1 w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:ring-2 focus:ring-red-500 focus:bg-white"
                />
              </div>
            </div>
          </div>

          {/* Step 2: SKU-Based Product Selection */}
          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-4">
            <h2 className="text-xs font-black uppercase tracking-wider text-slate-800 flex items-center space-x-2">
              <span className="w-5 h-5 rounded-full bg-red-600 text-white flex items-center justify-center text-[10px]">
                2
              </span>
              <span>SKU Product Entry</span>
            </h2>

            {/* Product Picker */}
            <div className="space-y-3 text-xs">
              <div>
                <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                  Select Product / SKU *
                </label>
                <div className="mt-1 grid grid-cols-1 sm:grid-cols-4 gap-2">
                  <div className="sm:col-span-3">
                    <select
                      value={selectedProductId}
                      onChange={(e) => setSelectedProductId(e.target.value)}
                      className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg font-bold text-slate-900 focus:ring-2 focus:ring-red-500 focus:bg-white"
                    >
                      {availableProducts.map((p) => (
                        <option key={p.id} value={p.id}>
                          [{p.sku}] {p.name} - {formatCurrency(p.unit_price)}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <input
                      type="number"
                      min={1}
                      value={inputQuantity}
                      onChange={(e) => setInputQuantity(parseInt(e.target.value) || 1)}
                      className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg font-black text-center text-slate-900 focus:ring-2 focus:ring-red-500 focus:bg-white"
                      placeholder="Qty"
                    />
                  </div>
                </div>
              </div>

              <button
                type="button"
                onClick={handleAddItem}
                className="w-full py-2.5 px-4 bg-slate-900 hover:bg-slate-800 text-white font-bold rounded-lg flex items-center justify-center space-x-1.5 transition shadow-sm"
              >
                <Plus className="w-4 h-4" />
                <span>Add Item to Quotation</span>
              </button>
            </div>

            {/* Added Items List */}
            <div className="pt-3 border-t border-slate-100">
              <h3 className="font-bold text-slate-700 text-[10px] uppercase tracking-wider mb-2">
                Quotation Line Items ({items.length})
              </h3>
              {calculation?.items && calculation.items.length > 0 ? (
                <div className="space-y-2">
                  {calculation.items.map((item, index) => (
                    <div
                      key={item.product_id}
                      className="p-3 bg-slate-50 border border-slate-200 rounded-xl flex items-center justify-between text-xs"
                    >
                      <div className="space-y-0.5 overflow-hidden pr-2">
                        <div className="font-mono font-bold text-red-600">{item.sku}</div>
                        <div className="font-bold text-slate-900 truncate">{item.product_name}</div>
                        <div className="text-[10px] text-slate-500">
                          {formatCurrency(item.unit_price)} &times; {item.quantity} unit{item.quantity > 1 ? "s" : ""}
                        </div>
                      </div>
                      <div className="flex items-center space-x-3 shrink-0">
                        <span className="font-black text-slate-900">{formatCurrency(item.total_price)}</span>
                        <button
                          type="button"
                          onClick={() => handleRemoveItem(index)}
                          className="p-1 rounded text-slate-400 hover:text-red-600 hover:bg-red-50 transition"
                          title="Remove item"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="py-6 text-center text-slate-400 text-xs">
                  No items added yet. Select an SKU above and click "Add Item".
                </div>
              )}
            </div>
          </div>

          {/* Step 3: Promotional Coupon */}
          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-3">
            <h2 className="text-xs font-black uppercase tracking-wider text-slate-800 flex items-center space-x-2">
              <Ticket className="w-4 h-4 text-red-600" />
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
                  className="flex-1 p-2.5 bg-slate-50 border border-slate-200 rounded-lg font-mono font-bold text-xs focus:ring-2 focus:ring-red-500 focus:bg-white"
                />
                <button
                  type="submit"
                  disabled={!couponCode.trim()}
                  className="px-4 py-2.5 bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs rounded-lg transition disabled:opacity-40"
                >
                  Apply
                </button>
              </form>
            )}
          </div>
        </div>

        {/* Right Column: Branded Quotation Preview (Matching Reference) */}
        <div className="lg:col-span-5 space-y-4">
          <div className="bg-white rounded-2xl border-2 border-slate-300 shadow-xl overflow-hidden sticky top-20">
            {/* Live Preview Header */}
            <div className="bg-slate-900 text-white p-3 flex items-center justify-between text-xs font-bold">
              <span className="flex items-center space-x-1.5">
                <Eye className="w-4 h-4 text-red-500" />
                <span>Live Quotation Preview</span>
              </span>
              {calcLoading && <span className="text-[10px] text-red-400 animate-pulse">Calculating...</span>}
            </div>

            {/* Branded Quotation Sheet Simulation */}
            <div className="p-4 sm:p-5 space-y-4 text-xs bg-white text-slate-900">
              {/* Livguard Logo & Brand Tagline */}
              <div className="flex justify-between items-start border-b border-slate-100 pb-3">
                <div>
                  <div className="text-xl font-black text-red-600 tracking-tight">Livguard</div>
                  <div className="text-[9px] font-bold text-slate-500 tracking-wider uppercase">
                    More Power. Less Waiting.
                  </div>
                </div>
                <div className="text-right">
                  <span className="px-2 py-0.5 rounded bg-slate-900 text-white font-bold text-[9px]">
                    LITHIUM-X SERIES
                  </span>
                </div>
              </div>

              {/* Title Bar */}
              <div className="bg-red-600 text-white py-1.5 px-3 rounded font-black text-center text-xs tracking-wider uppercase">
                Official Quotation Preview
              </div>

              {/* Customer Meta */}
              <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 space-y-1 text-[11px]">
                <div className="flex justify-between">
                  <span className="text-slate-500">Customer:</span>
                  <span className="font-bold text-slate-900">{customerName || "Customer Name"}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Mobile:</span>
                  <span className="font-semibold text-slate-800">{customerMobile || "Mobile Number"}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Quotation No:</span>
                  <span className="font-mono font-bold text-red-600">Auto-assigned upon Issue</span>
                </div>
              </div>

              {/* Items Preview Table */}
              <div className="border border-slate-200 rounded-lg overflow-hidden">
                <table className="w-full text-left text-[11px]">
                  <thead className="bg-slate-900 text-white uppercase text-[9px] font-bold">
                    <tr>
                      <th className="py-2 px-2.5">Product / SKU</th>
                      <th className="py-2 px-1 text-center">Qty</th>
                      <th className="py-2 px-2.5 text-right">Total</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {calculation?.items && calculation.items.length > 0 ? (
                      calculation.items.map((itm) => (
                        <tr key={itm.product_id}>
                          <td className="py-2 px-2.5">
                            <div className="font-bold text-slate-900 leading-tight">{itm.product_name}</div>
                            <div className="font-mono text-[9px] text-red-600">{itm.sku}</div>
                          </td>
                          <td className="py-2 px-1 text-center font-bold text-slate-800">{itm.quantity}</td>
                          <td className="py-2 px-2.5 text-right font-black text-slate-900">
                            {formatCurrency(itm.total_price)}
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={3} className="py-6 text-center text-slate-400 text-xs">
                          Add items to preview financial totals
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>

              {/* Financial Summary */}
              {calculation && (
                <div className="space-y-1.5 pt-2 border-t border-slate-100 text-xs">
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
                  <div className="flex justify-between p-2.5 rounded-lg bg-red-600 text-white font-black text-sm">
                    <span>Grand Total:</span>
                    <span>{formatCurrency(calculation.grand_total)}</span>
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
                className="w-full py-3 bg-red-600 hover:bg-red-700 text-white font-black text-xs uppercase tracking-wider rounded-xl shadow-lg shadow-red-600/30 transition flex items-center justify-center space-x-2 disabled:opacity-50"
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
                className="w-full py-2.5 bg-white border border-slate-200 hover:bg-slate-100 text-slate-700 font-bold text-xs rounded-xl transition flex items-center justify-center space-x-1.5 disabled:opacity-50"
              >
                <Save className="w-3.5 h-3.5" />
                <span>Save as Draft</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
