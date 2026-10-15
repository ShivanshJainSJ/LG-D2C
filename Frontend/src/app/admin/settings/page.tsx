"use client";

import { useEffect, useState } from "react";
import { Settings, Shield, Building2, Percent, Check, AlertCircle, Save } from "lucide-react";
import { api } from "@/lib/api";

interface CompanySettingsData {
  company_name: string;
  tagline: string;
  address: string;
  phone: string;
  email: string;
  website: string;
  terms_conditions: string;
  quotation_validity_days: number;
  numbering_policy: "CALENDAR_YEAR" | "FINANCIAL_YEAR" | "CONTINUOUS";
  version: number;
}

interface TaxSettingsData {
  gst_rate: number;
  pricing_policy: "EXCLUSIVE" | "INCLUSIVE";
  tax_name: string;
  is_active: boolean;
  version: number;
}

export default function AdminSettingsPage() {
  const [activeTab, setActiveTab] = useState<"company" | "tax">("company");
  const [loading, setLoading] = useState(true);
  const [saveLoading, setSaveLoading] = useState(false);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const [company, setCompany] = useState<CompanySettingsData>({
    company_name: "",
    tagline: "",
    address: "",
    phone: "",
    email: "",
    website: "",
    terms_conditions: "",
    quotation_validity_days: 15,
    numbering_policy: "CALENDAR_YEAR",
    version: 1,
  });

  const [tax, setTax] = useState<TaxSettingsData>({
    gst_rate: 18.0,
    pricing_policy: "EXCLUSIVE",
    tax_name: "GST",
    is_active: true,
    version: 1,
  });

  const fetchSettings = async () => {
    try {
      setLoading(true);
      const [compData, taxData] = await Promise.all([
        api.get<CompanySettingsData>("/admin/settings/company"),
        api.get<TaxSettingsData>("/admin/settings/tax"),
      ]);
      setCompany(compData);
      setTax(taxData);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSettings();
  }, []);

  const handleCompanySave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSuccessMsg(null);
    setErrorMsg(null);
    setSaveLoading(true);

    try {
      const updated = await api.put<CompanySettingsData>("/admin/settings/company", company);
      setCompany(updated);
      setSuccessMsg("Company details and quotation terms saved successfully.");
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to update company settings.");
    } finally {
      setSaveLoading(false);
    }
  };

  const handleTaxSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSuccessMsg(null);
    setErrorMsg(null);
    setSaveLoading(true);

    try {
      const updated = await api.put<TaxSettingsData>("/admin/settings/tax", {
        gst_rate: parseFloat(String(tax.gst_rate)),
        pricing_policy: tax.pricing_policy,
        tax_name: tax.tax_name,
        is_active: tax.is_active,
      });
      setTax(updated);
      setSuccessMsg("Statutory GST and tax calculation policy updated successfully.");
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to update tax configuration.");
    } finally {
      setSaveLoading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-black text-slate-900 tracking-tight">System & Statutory Settings</h1>
        <p className="text-xs text-slate-500 mt-1">
          Configure Livguard corporate details, quotation numbering sequences, and tax computation policies
        </p>
      </div>

      {/* Tabs */}
      <div className="flex items-center space-x-2 border-b border-slate-200 pb-3">
        <button
          onClick={() => setActiveTab("company")}
          className={`px-4 py-2 rounded-lg text-xs font-bold transition flex items-center space-x-2 ${
            activeTab === "company"
              ? "bg-red-600 text-white shadow-sm"
              : "bg-white border border-slate-200 text-slate-700 hover:bg-slate-50"
          }`}
        >
          <Building2 className="w-4 h-4" />
          <span>Company & Quotation Rules</span>
        </button>
        <button
          onClick={() => setActiveTab("tax")}
          className={`px-4 py-2 rounded-lg text-xs font-bold transition flex items-center space-x-2 ${
            activeTab === "tax"
              ? "bg-red-600 text-white shadow-sm"
              : "bg-white border border-slate-200 text-slate-700 hover:bg-slate-50"
          }`}
        >
          <Percent className="w-4 h-4" />
          <span>GST & Tax Calculation</span>
        </button>
      </div>

      {successMsg && (
        <div className="p-3.5 bg-emerald-50 border border-emerald-200 rounded-xl flex items-center space-x-2 text-xs font-semibold text-emerald-800">
          <Check className="w-4 h-4 text-emerald-600 shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      {errorMsg && (
        <div className="p-3.5 bg-red-50 border border-red-200 rounded-xl flex items-center space-x-2 text-xs font-semibold text-red-800">
          <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Company Form */}
      {activeTab === "company" && (
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
          <form onSubmit={handleCompanySave} className="space-y-5 text-xs">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <h3 className="text-sm font-bold text-slate-900">Corporate Branding & Information</h3>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Applied to all newly generated quotation and order documents
                </p>
              </div>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-slate-100 text-slate-600">
                Config v{company.version}
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                  Authorized Entity Name *
                </label>
                <input
                  type="text"
                  required
                  value={company.company_name}
                  onChange={(e) => setCompany({ ...company, company_name: e.target.value })}
                  className="mt-1 w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg font-bold text-slate-900 focus:ring-2 focus:ring-red-500 focus:bg-white"
                />
              </div>

              <div>
                <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                  Brand Tagline
                </label>
                <input
                  type="text"
                  value={company.tagline}
                  onChange={(e) => setCompany({ ...company, tagline: e.target.value })}
                  className="mt-1 w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:ring-2 focus:ring-red-500 focus:bg-white"
                />
              </div>
            </div>

            <div>
              <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                Registered Corporate Address *
              </label>
              <textarea
                rows={2}
                required
                value={company.address}
                onChange={(e) => setCompany({ ...company, address: e.target.value })}
                className="mt-1 w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:ring-2 focus:ring-red-500 focus:bg-white"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                  Toll-Free Support Phone *
                </label>
                <input
                  type="text"
                  required
                  value={company.phone}
                  onChange={(e) => setCompany({ ...company, phone: e.target.value })}
                  className="mt-1 w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:ring-2 focus:ring-red-500 focus:bg-white"
                />
              </div>

              <div>
                <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                  Official Support Email *
                </label>
                <input
                  type="email"
                  required
                  value={company.email}
                  onChange={(e) => setCompany({ ...company, email: e.target.value })}
                  className="mt-1 w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:ring-2 focus:ring-red-500 focus:bg-white"
                />
              </div>

              <div>
                <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">Website</label>
                <input
                  type="text"
                  value={company.website}
                  onChange={(e) => setCompany({ ...company, website: e.target.value })}
                  className="mt-1 w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:ring-2 focus:ring-red-500 focus:bg-white"
                />
              </div>
            </div>

            <div className="pt-4 border-t border-slate-100 grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                  Quotation Numbering Policy *
                </label>
                <select
                  value={company.numbering_policy}
                  onChange={(e) =>
                    setCompany({
                      ...company,
                      numbering_policy: e.target.value as "CALENDAR_YEAR" | "FINANCIAL_YEAR" | "CONTINUOUS",
                    })
                  }
                  className="mt-1 w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg font-bold text-slate-900 focus:ring-2 focus:ring-red-500 focus:bg-white"
                >
                  <option value="CALENDAR_YEAR">Calendar Year (LG/26/0001)</option>
                  <option value="FINANCIAL_YEAR">Financial Year (LG/26-27/0001)</option>
                  <option value="CONTINUOUS">Continuous Sequence (LG/000001)</option>
                </select>
                <span className="text-[10px] text-slate-400 mt-1 block">
                  Changing numbering policy does not rewrite historical quotation numbers.
                </span>
              </div>

              <div>
                <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                  Quotation Validity (Days) *
                </label>
                <input
                  type="number"
                  min={1}
                  max={90}
                  required
                  value={company.quotation_validity_days}
                  onChange={(e) => setCompany({ ...company, quotation_validity_days: parseInt(e.target.value) || 15 })}
                  className="mt-1 w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg font-bold text-slate-900 focus:ring-2 focus:ring-red-500 focus:bg-white"
                />
              </div>
            </div>

            <div>
              <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                Standard Terms & Conditions *
              </label>
              <textarea
                rows={5}
                required
                value={company.terms_conditions}
                onChange={(e) => setCompany({ ...company, terms_conditions: e.target.value })}
                className="mt-1 w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg font-mono text-[11px] focus:ring-2 focus:ring-red-500 focus:bg-white"
              />
            </div>

            <div className="flex justify-end pt-3">
              <button
                type="submit"
                disabled={saveLoading}
                className="px-6 py-2.5 bg-red-600 hover:bg-red-700 text-white font-bold rounded-lg shadow-md shadow-red-600/30 transition flex items-center space-x-2 disabled:opacity-50"
              >
                <Save className="w-4 h-4" />
                <span>{saveLoading ? "Saving..." : "Save Company Configuration"}</span>
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Tax Form */}
      {activeTab === "tax" && (
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
          <form onSubmit={handleTaxSave} className="space-y-5 text-xs">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <h3 className="text-sm font-bold text-slate-900">GST & Tax Calculation Policy</h3>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Controls statutory tax rates applied during quotation issuance and revision
                </p>
              </div>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-slate-100 text-slate-600">
                Tax Version v{tax.version}
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                  Applicable GST Rate (%) *
                </label>
                <input
                  type="number"
                  step="0.01"
                  min={0}
                  max={100}
                  required
                  value={tax.gst_rate}
                  onChange={(e) => setTax({ ...tax, gst_rate: parseFloat(e.target.value) || 0 })}
                  className="mt-1 w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg font-black text-slate-900 focus:ring-2 focus:ring-red-500 focus:bg-white"
                />
              </div>

              <div>
                <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                  Pricing & Tax Calculation Policy *
                </label>
                <select
                  value={tax.pricing_policy}
                  onChange={(e) =>
                    setTax({
                      ...tax,
                      pricing_policy: e.target.value as "EXCLUSIVE" | "INCLUSIVE",
                    })
                  }
                  className="mt-1 w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg font-bold text-slate-900 focus:ring-2 focus:ring-red-500 focus:bg-white"
                >
                  <option value="EXCLUSIVE">Tax Exclusive (Subtotal + GST = Grand Total)</option>
                  <option value="INCLUSIVE">Tax Inclusive (Prices include statutory GST)</option>
                </select>
              </div>
            </div>

            <div>
              <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                Tax Name / Display Label *
              </label>
              <input
                type="text"
                required
                value={tax.tax_name}
                onChange={(e) => setTax({ ...tax, tax_name: e.target.value })}
                placeholder="GST (18%)"
                className="mt-1 w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:ring-2 focus:ring-red-500 focus:bg-white"
              />
            </div>

            <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 text-slate-600 space-y-1">
              <strong className="text-slate-900">Tax Audit Notice:</strong>
              <p className="text-[11px]">
                Statutory tax modifications create an incremented configuration version. Changes apply exclusively to newly calculated quotations and revisions, ensuring absolute legal and accounting integrity for previously issued documents.
              </p>
            </div>

            <div className="flex justify-end pt-3">
              <button
                type="submit"
                disabled={saveLoading}
                className="px-6 py-2.5 bg-red-600 hover:bg-red-700 text-white font-bold rounded-lg shadow-md shadow-red-600/30 transition flex items-center space-x-2 disabled:opacity-50"
              >
                <Save className="w-4 h-4" />
                <span>{saveLoading ? "Saving..." : "Commit Tax Configuration"}</span>
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
