"use client";

import { useState } from "react";
import {
  X,
  Share2,
  Copy,
  Check,
  ExternalLink,
  Download,
  AlertTriangle,
  Loader2,
  RefreshCw,
} from "lucide-react";
import { api } from "@/lib/api";

interface ShareQuotationModalProps {
  isOpen: boolean;
  onClose: () => void;
  quotationId: string;
  quotationNumber: string;
  revisionId: string;
  revisionNumber: number;
  revisionLabel: string;
  onLinkCreated?: () => void;
}

export function ShareQuotationModal({
  isOpen,
  onClose,
  quotationId,
  quotationNumber,
  revisionId,
  revisionNumber,
  revisionLabel,
  onLinkCreated,
}: ShareQuotationModalProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [shareUrl, setShareUrl] = useState<string | null>(null);
  const [rawToken, setRawToken] = useState<string | null>(null);
  const [shortCode, setShortCode] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [activeLinkExists, setActiveLinkExists] = useState(false);

  if (!isOpen) return null;

  const handleGenerate = async (regenerate: boolean = false) => {
    setLoading(true);
    setError(null);
    setCopied(false);

    try {
      const res = await api.post<any>(
        `/agent/quotations/${quotationId}/revisions/${revisionId}/share?regenerate=${regenerate}`
      );

      if (res.active_link_exists && !res.is_new) {
        setActiveLinkExists(true);
        setShareUrl(null);
        setRawToken(null);
        setShortCode(null);
      } else if (res.is_new && (res.short_code || res.raw_token)) {
        setActiveLinkExists(false);
        const appBase = process.env.NEXT_PUBLIC_APP_URL || (typeof window !== "undefined" ? window.location.origin : "");
        const cleanQuoteNum = (res.quotation_number || quotationNumber || "QUOTE")
          .replace(/[^a-zA-Z0-9]+/g, "-")
          .replace(/^-+|-+$/g, "");
        const code = res.short_code || res.raw_token;
        const fullUrl = res.share_url
          ? `${appBase.replace(/\/$/, "")}${res.share_url}`
          : `${appBase.replace(/\/$/, "")}/q/${cleanQuoteNum}/${code}`;
        setShareUrl(fullUrl);
        setRawToken(res.raw_token);
        setShortCode(res.short_code || null);
        if (onLinkCreated) onLinkCreated();
      }
    } catch (err: any) {
      setError(err.message || "Failed to generate sharing link.");
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = () => {
    if (!shareUrl) return;
    navigator.clipboard.writeText(shareUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  const handleDownloadPdf = () => {
    const code = shortCode || rawToken;
    if (!code) return;
    const cleanQuoteNum = (quotationNumber || "QUOTE")
      .replace(/[^a-zA-Z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "");
    window.open(`/q/${cleanQuoteNum}/${code}`, "_blank");
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-200 relative">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-100">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 bg-red-50 text-red-600 rounded-xl">
              <Share2 className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-900">
                Share Quotation Link
              </h2>
              <p className="text-xs text-slate-500">
                {quotationNumber} &bull; {revisionLabel} (Rev {revisionNumber})
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="py-5 space-y-4">
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-xs text-red-700 flex items-start space-x-2">
              <AlertTriangle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {!shareUrl && !activeLinkExists && (
            <div className="text-center py-4 space-y-3">
              <p className="text-xs text-slate-600 max-w-sm mx-auto">
                Generate an unguessable public link for your customer to view
                and download the exact sealed PDF for{" "}
                <strong>{revisionLabel}</strong>.
              </p>
              <button
                type="button"
                onClick={() => handleGenerate(false)}
                disabled={loading}
                className="px-5 py-2.5 bg-red-600 hover:bg-red-700 text-white font-bold text-xs rounded-xl shadow-sm transition inline-flex items-center space-x-2 disabled:opacity-50"
              >
                {loading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Share2 className="w-4 h-4" />
                )}
                <span>Generate Public Link</span>
              </button>
            </div>
          )}

          {/* Active link already exists notice */}
          {activeLinkExists && !shareUrl && (
            <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl space-y-3 text-xs text-amber-900">
              <div className="flex items-start space-x-2">
                <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                <div>
                  <strong className="block text-amber-800">
                    Active Link Already Exists
                  </strong>
                  <span>
                    An active sharing link has already been created for this
                    revision. For security reasons, raw tokens are not stored on
                    the server and cannot be reconstructed.
                  </span>
                </div>
              </div>
              <div className="pt-2 flex items-center justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => handleGenerate(true)}
                  disabled={loading}
                  className="px-3.5 py-1.5 bg-amber-600 hover:bg-amber-700 text-white font-bold text-xs rounded-lg shadow-sm transition inline-flex items-center space-x-1.5 disabled:opacity-50"
                >
                  {loading ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <RefreshCw className="w-3.5 h-3.5" />
                  )}
                  <span>Regenerate New Link</span>
                </button>
              </div>
            </div>
          )}

          {/* Newly Generated Share Link View */}
          {shareUrl && (
            <div className="space-y-4">
              <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-xs text-emerald-800 flex items-center space-x-2">
                <Check className="w-4 h-4 text-emerald-600 shrink-0" />
                <span>
                  Public link created successfully! Copy it now to share with
                  your customer.
                </span>
              </div>

              <div>
                <label className="block text-[11px] font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                  Public Share Link
                </label>
                <div className="flex items-center space-x-2">
                  <input
                    type="text"
                    readOnly
                    value={shareUrl}
                    className="w-full px-3 py-2 text-xs font-mono bg-slate-50 border border-slate-200 rounded-lg text-slate-800 focus:outline-none"
                  />
                  <button
                    type="button"
                    onClick={copyToClipboard}
                    className="px-3 py-2 bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs rounded-lg transition inline-flex items-center space-x-1.5 shrink-0"
                  >
                    {copied ? (
                      <>
                        <Check className="w-3.5 h-3.5 text-emerald-400" />
                        <span>Copied!</span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-3.5 h-3.5" />
                        <span>Copy</span>
                      </>
                    )}
                  </button>
                </div>
              </div>

              {/* Action shortcuts */}
              <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-100">
                <a
                  href={shareUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold text-xs rounded-lg transition inline-flex items-center space-x-1"
                >
                  <ExternalLink className="w-3.5 h-3.5 text-slate-500" />
                  <span>Open Page</span>
                </a>
                <button
                  type="button"
                  onClick={handleDownloadPdf}
                  className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold text-xs rounded-lg transition inline-flex items-center space-x-1"
                >
                  <Download className="w-3.5 h-3.5 text-red-600" />
                  <span>Download PDF</span>
                </button>
                <button
                  type="button"
                  onClick={() => handleGenerate(true)}
                  disabled={loading}
                  className="ml-auto text-[11px] text-slate-400 hover:text-slate-600 font-semibold inline-flex items-center space-x-1 transition"
                >
                  <RefreshCw className="w-3 h-3" />
                  <span>Generate another</span>
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="pt-3 border-t border-slate-100 flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-xs font-bold text-slate-600 hover:text-slate-900 rounded-lg hover:bg-slate-100 transition"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
