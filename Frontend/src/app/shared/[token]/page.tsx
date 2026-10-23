"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import {
  FileText,
  FileDown,
  ShieldCheck,
  AlertCircle,
  Loader2,
  Calendar,
  User,
  Phone,
  Building,
  CheckCircle2,
} from "lucide-react";
import { formatCurrency, amountToWordsINR } from "@/lib/utils";
import { getProductCategoryImage } from "@/lib/productCategories";

interface PublicItem {
  product_name: string;
  sku: string;
  description: string | null;
  quantity: number;
  unit_price: number;
  total_price: number;
  image_url: string | null;
}

interface PublicQuotation {
  quotation_number: string;
  revision_label: string;
  customer_name: string;
  issue_date: string;
  validity_days: number;
  expiry_date: string;
  subtotal: number;
  discount_amount: number;
  tax_rate: number;
  tax_amount: number;
  grand_total: number;
  agent_name: string;
  agent_mobile: string | null;
  items: PublicItem[];
  pdf_download_url: string;
}

export default function PublicSharedQuotationPage() {
  const params = useParams();
  const token = params?.token as string;

  const [quotation, setQuotation] = useState<PublicQuotation | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showPdfViewer, setShowPdfViewer] = useState(false);

  useEffect(() => {
    if (!token) return;

    const fetchPublicQuotation = async () => {
      try {
        setLoading(true);
        setError(null);

        const apiBase = process.env.NEXT_PUBLIC_API_URL
          ? `${process.env.NEXT_PUBLIC_API_URL.replace(/\/$/, "")}/api/v1`
          : "/api/v1";
        const res = await fetch(`${apiBase}/public/quotations/${token}`);

        if (res.status === 404) {
          setError(
            "This quotation link is invalid, has expired, or has been revoked by the sales representative."
          );
          return;
        }

        if (res.status === 429) {
          setError("Rate limit exceeded. Please wait a minute and refresh the page.");
          return;
        }

        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          throw new Error(body.detail || "Unable to retrieve quotation details.");
        }

        const data: PublicQuotation = await res.json();
        setQuotation(data);
      } catch (err: any) {
        setError(err.message || "An unexpected error occurred while loading this quotation.");
      } finally {
        setLoading(false);
      }
    };

    fetchPublicQuotation();
  }, [token]);

  const apiBase = process.env.NEXT_PUBLIC_API_URL
    ? `${process.env.NEXT_PUBLIC_API_URL.replace(/\/$/, "")}/api/v1`
    : "/api/v1";
  const pdfUrl = token ? `${apiBase}/public/quotations/${token}/pdf` : "";

  const handleDownload = () => {
    if (!pdfUrl) return;
    window.open(pdfUrl, "_blank");
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-100 flex flex-col items-center justify-center p-6 text-center">
        <div className="bg-white p-8 rounded-3xl border border-slate-200 shadow-xl max-w-sm w-full flex flex-col items-center">
          <div className="w-14 h-14 rounded-2xl bg-red-50 text-red-600 flex items-center justify-center mb-4">
            <Loader2 className="w-7 h-7 animate-spin" />
          </div>
          <h2 className="text-base font-bold text-slate-900">Loading Quotation</h2>
          <p className="text-xs text-slate-500 mt-1">
            Verifying secure customer access token...
          </p>
        </div>
      </div>
    );
  }

  if (error || !quotation) {
    return (
      <div className="min-h-screen bg-slate-100 flex flex-col items-center justify-center p-6 text-center">
        <div className="bg-white p-8 rounded-3xl border border-slate-200 shadow-xl max-w-md w-full flex flex-col items-center">
          <div className="w-14 h-14 rounded-2xl bg-amber-50 text-amber-600 flex items-center justify-center mb-4">
            <AlertCircle className="w-7 h-7" />
          </div>
          <h2 className="text-lg font-black text-slate-900">Quotation Unavailable</h2>
          <p className="text-xs text-slate-600 mt-2 leading-relaxed">
            {error || "Quotation could not be located."}
          </p>
          <div className="mt-6 p-4 bg-slate-50 rounded-2xl border border-slate-200 text-[11px] text-slate-500 text-left w-full space-y-1">
            <p className="font-semibold text-slate-700">Need assistance?</p>
            <p>
              Please contact your Livguard sales executive or dealer to obtain an updated quotation link.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-100 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Top Floating Action Header */}
        <div className="bg-white/80 backdrop-blur-md sticky top-4 z-20 rounded-2xl border border-slate-200/80 shadow-md p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 bg-red-600 text-white rounded-xl shadow-sm">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h1 className="text-base font-black text-slate-900">
                  {quotation.quotation_number}
                </h1>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-100 text-slate-700 border border-slate-200">
                  {quotation.revision_label}
                </span>
              </div>
              <p className="text-xs text-slate-500">
                Prepared for <strong className="text-slate-800">{quotation.customer_name}</strong>
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2.5 w-full sm:w-auto">
            <button
              onClick={() => setShowPdfViewer(!showPdfViewer)}
              className="flex-1 sm:flex-none px-4 py-2 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-bold transition shadow-sm"
            >
              {showPdfViewer ? "Hide PDF Viewer" : "View Official PDF"}
            </button>
            <button
              onClick={handleDownload}
              className="flex-1 sm:flex-none px-5 py-2 rounded-xl bg-red-600 hover:bg-red-700 text-white text-xs font-bold transition shadow-md shadow-red-600/30 flex items-center justify-center space-x-2"
            >
              <FileDown className="w-4 h-4" />
              <span>Download PDF</span>
            </button>
          </div>
        </div>

        {/* Inline PDF Viewer (Toggled) */}
        {showPdfViewer && (
          <div className="bg-white rounded-2xl border border-slate-200 shadow-md overflow-hidden">
            <div className="p-3 bg-slate-900 text-white text-xs font-bold flex items-center justify-between">
              <span className="flex items-center space-x-2">
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
                <span>Verified Immutable PDF Document</span>
              </span>
              <button
                onClick={() => setShowPdfViewer(false)}
                className="text-slate-400 hover:text-white text-xs px-2 py-1 rounded"
              >
                Close
              </button>
            </div>
            <div className="w-full h-[750px] bg-slate-200">
              <iframe
                src={`${pdfUrl}#toolbar=1&navpanes=0`}
                className="w-full h-full border-0"
                title="Quotation PDF Document"
              />
            </div>
          </div>
        )}

        {/* Main Document Presentation */}
        <div className="bg-white rounded-3xl border border-slate-200 shadow-xl overflow-hidden">
          {/* Header Banner */}
          <div className="p-6 border-b border-slate-200 bg-gradient-to-b from-white to-slate-50 space-y-4">
            <img
              src="/assets/Banner.png"
              alt="Livguard Banner"
              className="w-full h-auto rounded-xl object-contain block"
            />
            <img
              src="/assets/LogoQuotation.png"
              alt="Livguard Quotation"
              className="w-full h-auto object-contain block"
            />
          </div>

          <div className="p-6 sm:p-8 space-y-6 text-xs">
            {/* Metadata Info Panel */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 bg-slate-50 p-5 rounded-2xl border border-slate-200">
              <div className="space-y-1.5">
                <span className="text-[10px] font-bold uppercase tracking-wider text-red-600 block">
                  Customer Information
                </span>
                <p className="text-base font-black text-slate-900">{quotation.customer_name}</p>
                <div className="flex items-center space-x-1.5 text-slate-600 pt-1">
                  <User className="w-3.5 h-3.5 text-slate-400" />
                  <span>Representative: {quotation.agent_name}</span>
                </div>
                {quotation.agent_mobile && (
                  <div className="flex items-center space-x-1.5 text-slate-600">
                    <Phone className="w-3.5 h-3.5 text-slate-400" />
                    <span>Contact: {quotation.agent_mobile}</span>
                  </div>
                )}
              </div>

              <div className="space-y-1.5 sm:border-l sm:border-slate-200 sm:pl-4">
                <span className="text-[10px] font-bold uppercase tracking-wider text-red-600 block">
                  Quotation Details
                </span>
                <p className="text-slate-700">
                  Quotation No: <strong>{quotation.quotation_number}</strong>
                </p>
                <p className="text-slate-700">
                  Version: <strong>{quotation.revision_label}</strong>
                </p>
                <div className="flex items-center space-x-1.5 text-slate-600 pt-1">
                  <Calendar className="w-3.5 h-3.5 text-slate-400" />
                  <span>Date Issued: {quotation.issue_date}</span>
                </div>
                <div className="flex items-center space-x-1.5 text-emerald-700 font-medium">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                  <span>Valid for {quotation.validity_days} days (Until {quotation.expiry_date})</span>
                </div>
              </div>
            </div>

            {/* Line Items Table */}
            <div className="border border-slate-200 rounded-2xl overflow-hidden shadow-sm">
              <table className="w-full text-left">
                <thead className="bg-slate-900 text-white text-[10px] uppercase font-bold tracking-wider">
                  <tr>
                    <th className="py-3 px-3.5 text-center">S.No.</th>
                    <th className="py-3 px-3.5">Product</th>
                    <th className="py-3 px-3.5 text-center">SKU / Model</th>
                    <th className="py-3 px-3.5">Description</th>
                    <th className="py-3 px-3.5 text-center">Qty.</th>
                    <th className="py-3 px-3.5 text-right">Unit Price</th>
                    <th className="py-3 px-3.5 text-right">Total Price</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {quotation.items.map((item, idx) => (
                    <tr key={idx} className="hover:bg-slate-50/50">
                      <td className="py-3 px-3.5 text-center text-slate-500 font-bold">{idx + 1}</td>
                      <td className="py-3 px-3.5">
                        <div className="w-12 h-12 bg-white rounded-xl border border-slate-200 p-1 flex items-center justify-center overflow-hidden">
                          <img
                            src={getProductCategoryImage(null, item.image_url)}
                            alt={item.product_name}
                            className="w-full h-full object-contain"
                            onError={(e) => {
                              (e.target as HTMLImageElement).src = "/uploads/products/inverter.png";
                            }}
                          />
                        </div>
                      </td>
                      <td className="py-3 px-3.5 text-center font-mono font-bold text-red-600 text-xs">
                        {item.sku}
                      </td>
                      <td className="py-3 px-3.5">
                        <div className="font-bold text-slate-900 text-xs">{item.product_name}</div>
                        {item.description && (
                          <div className="text-[10px] text-slate-500 mt-0.5 line-clamp-2">
                            {item.description.replace(/\n/g, " • ")}
                          </div>
                        )}
                      </td>
                      <td className="py-3 px-3.5 text-center font-bold text-slate-800 text-xs">
                        {item.quantity}
                      </td>
                      <td className="py-3 px-3.5 text-right font-medium text-slate-700">
                        {formatCurrency(item.unit_price)}
                      </td>
                      <td className="py-3 px-3.5 text-right font-black text-slate-900 text-xs">
                        {formatCurrency(item.total_price)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Totals Summary */}
            <div className="flex flex-col items-end space-y-3">
              <div className="w-full sm:w-80 bg-slate-50 border border-slate-200 rounded-2xl p-4 space-y-2.5">
                <div className="flex justify-between text-slate-600">
                  <span>Subtotal:</span>
                  <span className="font-bold text-slate-900">{formatCurrency(quotation.subtotal)}</span>
                </div>
                {quotation.discount_amount > 0 && (
                  <div className="flex justify-between text-emerald-600 font-bold">
                    <span>Discount:</span>
                    <span>-{formatCurrency(quotation.discount_amount)}</span>
                  </div>
                )}
                <div className="flex justify-between text-slate-600">
                  <span>GST ({quotation.tax_rate}%):</span>
                  <span className="font-bold text-slate-900">{formatCurrency(quotation.tax_amount)}</span>
                </div>
                <div className="flex justify-between pt-2.5 border-t border-slate-200 text-base font-black text-red-600">
                  <span>Grand Total:</span>
                  <span>{formatCurrency(quotation.grand_total)}</span>
                </div>
              </div>

              {/* Amount in Words */}
              <div className="w-full bg-slate-50 border border-slate-200 border-l-4 border-l-red-600 rounded-xl p-3.5 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-1">
                <span className="font-black text-slate-900">Amount in Words:</span>
                <span className="font-bold text-red-700 italic">{amountToWordsINR(quotation.grand_total)}</span>
              </div>
            </div>

            {/* Trust and Verification Footer */}
            <div className="pt-6 border-t border-slate-200 flex flex-col sm:flex-row items-center justify-between gap-3 text-slate-400 text-[11px]">
              <div className="flex items-center space-x-2">
                <ShieldCheck className="w-4 h-4 text-emerald-600" />
                <span>Digitally issued and verified by Livguard Energy Technologies Pvt. Ltd.</span>
              </div>
              <div>This is an immutable quotation artifact.</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
