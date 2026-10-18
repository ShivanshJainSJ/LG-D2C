"use client";

import { useState, useRef } from "react";
import {
  X,
  Upload,
  FileSpreadsheet,
  FileText,
  Download,
  AlertTriangle,
  CheckCircle,
  XCircle,
  HelpCircle,
  Loader2,
  ArrowRight,
  ArrowLeft,
  RotateCcw,
  ShieldAlert,
  Copy,
  Check,
} from "lucide-react";
import { api } from "@/lib/api";
import { formatCurrency } from "@/lib/utils";
import { PRODUCT_CATEGORIES } from "@/lib/productCategories";

interface ProductImportModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

interface PreviewRow {
  row_idx: number;
  sku: string;
  product_name: string;
  category: string;
  category_key: string;
  description?: string;
  unit_price: number;
  image_url?: string;
  is_active?: boolean;
  is_valid: boolean;
  is_duplicate_in_file: boolean;
  is_existing_in_db: boolean;
  errors: string[];
  diff?: Record<string, { old: any; new: any }> | null;
}

interface PreviewData {
  filename: string;
  file_type: string;
  total_rows: number;
  valid_rows: number;
  invalid_rows: number;
  file_duplicate_skus_count: number;
  db_existing_skus_count: number;
  new_skus_count: number;
  can_import: boolean;
  summary: string;
  rows: PreviewRow[];
}

interface ExecuteResult {
  batch_id: string;
  filename: string;
  conflict_policy: string;
  total_rows: number;
  inserted_count: number;
  updated_count: number;
  skipped_count: number;
  rejected_count: number;
  status: string;
  message: string;
}

export function ProductImportModal({ isOpen, onClose, onSuccess }: ProductImportModalProps) {
  const [step, setStep] = useState<"upload" | "preview" | "result">("upload");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Preview State
  const [preview, setPreview] = useState<PreviewData | null>(null);
  const [conflictPolicy, setConflictPolicy] = useState<"skip" | "overwrite">("skip");
  const [overwriteConfirmed, setOverwriteConfirmed] = useState(false);
  const [previewFilter, setPreviewFilter] = useState<"all" | "errors" | "existing" | "new">("all");

  // Result State
  const [result, setResult] = useState<ExecuteResult | null>(null);

  // Copy header state
  const [copiedHeader, setCopiedHeader] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const handleCopyHeaders = () => {
    navigator.clipboard.writeText("sku,product_name,category,description,unit_price,image_url,is_active");
    setCopiedHeader(true);
    setTimeout(() => setCopiedHeader(false), 2000);
  };

  const handleDownloadTemplate = async (type: "xlsx" | "csv") => {
    try {
      await api.download(
        `/admin/products/import/template/${type}`,
        `Livguard_Product_Import_Template.${type}`
      );
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to download template.");
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setErrorMsg(null);
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      const ext = file.name.split(".").pop()?.toLowerCase();
      if (!["xlsx", "xls", "csv"].includes(ext || "")) {
        setErrorMsg("Only .xlsx and .csv spreadsheet files are supported.");
        return;
      }
      if (file.size > 5 * 1024 * 1024) {
        setErrorMsg("File size exceeds maximum allowed 5 MB.");
        return;
      }
      setSelectedFile(file);
    }
  };

  const handleAnalyzeFile = async () => {
    if (!selectedFile) {
      setErrorMsg("Please select an XLSX or CSV file to upload.");
      return;
    }
    setLoading(true);
    setErrorMsg(null);

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);
      const data = await api.post<PreviewData>("/admin/products/import/preview", formData);
      setPreview(data);
      setConflictPolicy("skip");
      setOverwriteConfirmed(false);
      setStep("preview");
    } catch (err: any) {
      setErrorMsg(err.message || "Validation error parsing file.");
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadErrorsCSV = () => {
    if (!preview) return;
    const errorRows = preview.rows.filter((r) => !r.is_valid);
    let csvContent = "data:text/csv;charset=utf-8,Row Number,SKU,Product Name,Validation Errors\n";
    errorRows.forEach((r) => {
      const cleanErrors = r.errors.join("; ").replace(/"/g, '""');
      const cleanName = (r.product_name || "").replace(/"/g, '""');
      csvContent += `${r.row_idx},"${r.sku}","${cleanName}","${cleanErrors}"\n`;
    });
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `Livguard_Import_Errors_${preview.filename}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleExecuteImport = async () => {
    if (!selectedFile || !preview) return;
    if (!preview.can_import) {
      setErrorMsg("Cannot import file containing errors. Please resolve errors and upload again.");
      return;
    }
    if (conflictPolicy === "overwrite" && !overwriteConfirmed) {
      setErrorMsg("Please acknowledge the overwrite confirmation checkbox before proceeding.");
      return;
    }

    setLoading(true);
    setErrorMsg(null);

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);
      formData.append("conflict_policy", conflictPolicy);
      formData.append("overwrite_confirmed", String(overwriteConfirmed));

      const res = await api.post<ExecuteResult>("/admin/products/import/execute", formData);
      setResult(res);
      setStep("result");
    } catch (err: any) {
      setErrorMsg(err.message || "Import execution failed.");
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadBatchReport = async () => {
    if (!result) return;
    try {
      await api.download(
        `/admin/products/import/history/${result.batch_id}/errors.csv`,
        `Livguard_Import_Report_${result.batch_id}.csv`
      );
    } catch (err: any) {
      setErrorMsg("Failed to download batch report.");
    }
  };

  const resetAll = () => {
    setStep("upload");
    setSelectedFile(null);
    setPreview(null);
    setResult(null);
    setErrorMsg(null);
    setConflictPolicy("skip");
    setOverwriteConfirmed(false);
  };

  const filteredPreviewRows = preview?.rows.filter((r) => {
    if (previewFilter === "errors") return !r.is_valid;
    if (previewFilter === "existing") return r.is_existing_in_db;
    if (previewFilter === "new") return !r.is_existing_in_db && r.is_valid;
    return true;
  }) || [];

  return (
    <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-3 sm:p-5 overflow-y-auto">
      <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-4xl w-full max-h-[92vh] flex flex-col relative overflow-hidden">
        {/* Header */}
        <div className="p-4 sm:p-5 border-b border-slate-200 bg-slate-50 flex items-center justify-between shrink-0">
          <div className="flex items-center space-x-2.5">
            <div className="w-9 h-9 rounded-xl bg-red-600 text-white flex items-center justify-center shadow-md shadow-red-600/20">
              <Upload className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-black text-slate-900 tracking-tight">Bulk Import Products</h2>
              <p className="text-[11px] text-slate-500">
                Official Livguard master catalog bulk upload via XLSX or CSV
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-200/50 rounded-lg transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Global Error Alert */}
        {errorMsg && (
          <div className="mx-5 mt-4 p-3 bg-red-50 border border-red-200 rounded-xl flex items-center space-x-2.5 text-xs text-red-700 font-semibold shrink-0">
            <AlertTriangle className="w-4 h-4 text-red-600 shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}

        {/* Body content */}
        <div className="p-5 overflow-y-auto flex-1 space-y-5 text-xs">
          {/* STEP 1: Upload & Instructions */}
          {step === "upload" && (
            <div className="space-y-5">
              {/* Mandatory Instructions & Disclaimer */}
              <div className="bg-amber-50/70 border border-amber-200 rounded-xl p-4 text-slate-800 space-y-2.5">
                <div className="flex items-center space-x-2 text-amber-900 font-extrabold text-xs uppercase tracking-wide">
                  <ShieldAlert className="w-4 h-4 text-amber-600 shrink-0" />
                  <span>Important Import Instructions & Disclaimer</span>
                </div>
                <div className="text-[11px] text-slate-700 space-y-1.5 leading-relaxed">
                  <p className="font-semibold text-slate-900">Before uploading your product file:</p>
                  <ul className="list-disc pl-4 space-y-1 text-slate-600">
                    <li>Use the downloadable Livguard template as the starting point.</li>
                    <li>Do not rename, remove, or rearrange column headers.</li>
                    <li>Save the file as <strong>.xlsx</strong> or <strong>.csv</strong>.</li>
                    <li>Every product must have a unique, non-empty SKU within the uploaded file.</li>
                    <li>SKU values are treated as text to preserve leading zeros and special characters.</li>
                    <li>
                      Category values must match one of the <strong>5 supported categories</strong> exactly (see list below).
                    </li>
                    <li>Unit prices must be valid non-negative numbers.</li>
                    <li>Optional fields may be left blank only where permitted.</li>
                    <li>Existing SKUs may match products already present in the database.</li>
                    <li>You will be shown a preview and asked how to handle existing SKU conflicts before any records are modified.</li>
                    <li>No products will be imported until you explicitly confirm the final import.</li>
                    <li>Importing with overwrite enabled can change existing product details. Review the conflict report carefully before proceeding.</li>
                  </ul>
                </div>
              </div>

              {/* Supported Categories Badge List */}
              <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl space-y-1.5">
                <span className="font-extrabold text-[10px] uppercase text-slate-500 tracking-wider">
                  5 Supported Product Categories:
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {PRODUCT_CATEGORIES.map((c) => (
                    <span
                      key={c.id}
                      className="px-2 py-0.5 rounded-full bg-white border border-slate-200 font-bold text-slate-800 text-[10.5px]"
                    >
                      {c.label}
                    </span>
                  ))}
                </div>
              </div>

              {/* Canonical Column Headers & Copy Box */}
              <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-extrabold text-[10px] uppercase text-slate-500 tracking-wider">
                    Canonical Column Headers (Exact Sequence Required):
                  </span>
                  <button
                    onClick={handleCopyHeaders}
                    className="inline-flex items-center space-x-1 text-[10.5px] font-bold text-red-600 hover:text-red-700"
                  >
                    {copiedHeader ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3" />}
                    <span>{copiedHeader ? "Copied!" : "Copy Headers"}</span>
                  </button>
                </div>
                <div className="font-mono text-[10.5px] bg-white p-2 rounded border border-slate-200 text-slate-700 select-all overflow-x-auto">
                  sku,product_name,category,description,unit_price,image_url,is_active
                </div>
              </div>

              {/* Download Templates Actions */}
              <div className="space-y-2">
                <span className="font-extrabold text-[10px] uppercase text-slate-500 tracking-wider block">
                  Download Official Starter Templates:
                </span>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <button
                    type="button"
                    onClick={() => handleDownloadTemplate("xlsx")}
                    className="p-3 bg-white border border-slate-200 rounded-xl hover:border-emerald-500 hover:bg-emerald-50/30 flex items-center space-x-3 transition group text-left shadow-sm"
                  >
                    <div className="w-9 h-9 rounded-lg bg-emerald-100 text-emerald-700 flex items-center justify-center shrink-0">
                      <FileSpreadsheet className="w-5 h-5" />
                    </div>
                    <div>
                      <div className="font-bold text-slate-900 group-hover:text-emerald-700">
                        Excel Template (.xlsx)
                      </div>
                      <div className="text-[10px] text-slate-400">Formatted with headers & sample row</div>
                    </div>
                  </button>

                  <button
                    type="button"
                    onClick={() => handleDownloadTemplate("csv")}
                    className="p-3 bg-white border border-slate-200 rounded-xl hover:border-blue-500 hover:bg-blue-50/30 flex items-center space-x-3 transition group text-left shadow-sm"
                  >
                    <div className="w-9 h-9 rounded-lg bg-blue-100 text-blue-700 flex items-center justify-center shrink-0">
                      <FileText className="w-5 h-5" />
                    </div>
                    <div>
                      <div className="font-bold text-slate-900 group-hover:text-blue-700">
                        CSV Template (.csv)
                      </div>
                      <div className="text-[10px] text-slate-400">Standard UTF-8 comma-separated template</div>
                    </div>
                  </button>
                </div>
              </div>

              {/* Upload Dropzone */}
              <div className="space-y-2">
                <span className="font-extrabold text-[10px] uppercase text-slate-500 tracking-wider block">
                  Upload Product Catalog File:
                </span>
                <div
                  onClick={() => fileInputRef.current?.click()}
                  className={`border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition ${
                    selectedFile
                      ? "border-emerald-500 bg-emerald-50/20"
                      : "border-slate-300 hover:border-red-500 hover:bg-slate-50"
                  }`}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".xlsx,.xls,.csv"
                    onChange={handleFileChange}
                    className="hidden"
                  />
                  <Upload className={`w-8 h-8 mx-auto mb-2 ${selectedFile ? "text-emerald-600" : "text-slate-400"}`} />
                  {selectedFile ? (
                    <div>
                      <span className="font-bold text-slate-900 text-sm">{selectedFile.name}</span>
                      <span className="text-[11px] text-slate-500 block mt-0.5">
                        {(selectedFile.size / 1024).toFixed(1)} KB &bull; Click to choose another file
                      </span>
                    </div>
                  ) : (
                    <div>
                      <span className="font-bold text-slate-800 text-xs">
                        Click to select or drag & drop your XLSX or CSV file
                      </span>
                      <span className="text-[10px] text-slate-400 block mt-1">Maximum 5,000 products &bull; 5 MB</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* STEP 2: Preview & Validation Table */}
          {step === "preview" && preview && (
            <div className="space-y-4">
              {/* Summary Badges */}
              <div className="grid grid-cols-2 sm:grid-cols-6 gap-2 text-center">
                <div className="p-2.5 bg-slate-50 border border-slate-200 rounded-xl">
                  <div className="text-base font-black text-slate-900">{preview.total_rows}</div>
                  <div className="text-[9px] font-bold text-slate-400 uppercase">Total Rows</div>
                </div>
                <div className="p-2.5 bg-emerald-50 border border-emerald-200 rounded-xl">
                  <div className="text-base font-black text-emerald-700">{preview.valid_rows}</div>
                  <div className="text-[9px] font-bold text-emerald-600 uppercase">Valid Rows</div>
                </div>
                <div
                  className={`p-2.5 rounded-xl border ${
                    preview.invalid_rows > 0
                      ? "bg-red-50 border-red-200 text-red-700"
                      : "bg-slate-50 border-slate-200 text-slate-400"
                  }`}
                >
                  <div className="text-base font-black">{preview.invalid_rows}</div>
                  <div className="text-[9px] font-bold uppercase">Invalid Rows</div>
                </div>
                <div
                  className={`p-2.5 rounded-xl border ${
                    preview.file_duplicate_skus_count > 0
                      ? "bg-red-50 border-red-200 text-red-700"
                      : "bg-slate-50 border-slate-200 text-slate-400"
                  }`}
                >
                  <div className="text-base font-black">{preview.file_duplicate_skus_count}</div>
                  <div className="text-[9px] font-bold uppercase">File Duplicates</div>
                </div>
                <div className="p-2.5 bg-amber-50 border border-amber-200 rounded-xl">
                  <div className="text-base font-black text-amber-700">{preview.db_existing_skus_count}</div>
                  <div className="text-[9px] font-bold text-amber-600 uppercase">In Database</div>
                </div>
                <div className="p-2.5 bg-purple-50 border border-purple-200 rounded-xl">
                  <div className="text-base font-black text-purple-700">{preview.new_skus_count}</div>
                  <div className="text-[9px] font-bold text-purple-600 uppercase">New Products</div>
                </div>
              </div>

              {/* Error Notice & Download Error Report */}
              {!preview.can_import && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-xl flex items-center justify-between gap-3 text-red-800">
                  <div className="flex items-center space-x-2">
                    <AlertTriangle className="w-4 h-4 text-red-600 shrink-0" />
                    <span className="font-semibold text-xs">
                      Fix the validation errors below before importing. Products cannot be committed with errors.
                    </span>
                  </div>
                  <button
                    onClick={handleDownloadErrorsCSV}
                    className="px-2.5 py-1 bg-white border border-red-200 text-red-700 hover:bg-red-100 rounded-lg font-bold text-[11px] flex items-center space-x-1 shrink-0"
                  >
                    <Download className="w-3.5 h-3.5" />
                    <span>Download Errors</span>
                  </button>
                </div>
              )}

              {/* Conflict Policy Selector (If existing SKUs in DB) */}
              {preview.db_existing_skus_count > 0 && preview.can_import && (
                <div className="p-4 bg-amber-50/70 border-2 border-amber-300 rounded-xl space-y-3">
                  <div>
                    <h3 className="text-xs font-black text-amber-900 uppercase tracking-wide">
                      Existing Products Found in Database ({preview.db_existing_skus_count} SKUs)
                    </h3>
                    <p className="text-[11px] text-amber-800 mt-0.5">
                      Choose how matching products already present in the Livguard catalog should be handled:
                    </p>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                    <label
                      className={`p-3 rounded-xl border cursor-pointer transition flex items-start space-x-2.5 ${
                        conflictPolicy === "skip"
                          ? "bg-white border-amber-600 shadow-sm"
                          : "bg-amber-100/40 border-amber-200"
                      }`}
                    >
                      <input
                        type="radio"
                        name="conflict_policy"
                        value="skip"
                        checked={conflictPolicy === "skip"}
                        onChange={() => {
                          setConflictPolicy("skip");
                          setOverwriteConfirmed(false);
                        }}
                        className="mt-0.5 text-red-600 focus:ring-red-500"
                      />
                      <div>
                        <div className="font-bold text-slate-900">Option 1: Skip Existing Products</div>
                        <div className="text-[10.5px] text-slate-500 mt-0.5">
                          Only insert new SKUs ({preview.new_skus_count}). Leave existing products unchanged.
                        </div>
                      </div>
                    </label>

                    <label
                      className={`p-3 rounded-xl border cursor-pointer transition flex items-start space-x-2.5 ${
                        conflictPolicy === "overwrite"
                          ? "bg-white border-red-600 shadow-sm"
                          : "bg-amber-100/40 border-amber-200"
                      }`}
                    >
                      <input
                        type="radio"
                        name="conflict_policy"
                        value="overwrite"
                        checked={conflictPolicy === "overwrite"}
                        onChange={() => setConflictPolicy("overwrite")}
                        className="mt-0.5 text-red-600 focus:ring-red-500"
                      />
                      <div>
                        <div className="font-bold text-slate-900">Option 2: Overwrite Existing Products</div>
                        <div className="text-[10.5px] text-slate-500 mt-0.5">
                          Update matching products ({preview.db_existing_skus_count}) using uploaded details & pricing.
                        </div>
                      </div>
                    </label>
                  </div>

                  {/* Overwrite Confirmation Checkbox */}
                  {conflictPolicy === "overwrite" && (
                    <div className="p-3 bg-red-100/60 border border-red-300 rounded-lg space-y-2">
                      <div className="flex items-start space-x-2">
                        <input
                          type="checkbox"
                          id="overwrite_confirm_cb"
                          checked={overwriteConfirmed}
                          onChange={(e) => setOverwriteConfirmed(e.target.checked)}
                          className="mt-1 w-4 h-4 text-red-600 rounded border-slate-300 focus:ring-red-500"
                        />
                        <label
                          htmlFor="overwrite_confirm_cb"
                          className="text-[11px] font-bold text-red-950 leading-tight cursor-pointer"
                        >
                          I understand that overwriting existing SKUs will update matching product records using the uploaded data. These changes may affect future quotations. I have reviewed the products that will be updated.
                        </label>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Table Filter Tabs */}
              <div className="flex items-center justify-between pt-1">
                <div className="flex items-center space-x-1.5">
                  <button
                    onClick={() => setPreviewFilter("all")}
                    className={`px-2.5 py-1 rounded-lg text-[10px] font-bold transition ${
                      previewFilter === "all" ? "bg-slate-900 text-white" : "bg-slate-100 text-slate-600"
                    }`}
                  >
                    All Rows ({preview.total_rows})
                  </button>
                  {preview.invalid_rows > 0 && (
                    <button
                      onClick={() => setPreviewFilter("errors")}
                      className={`px-2.5 py-1 rounded-lg text-[10px] font-bold transition ${
                        previewFilter === "errors" ? "bg-red-600 text-white" : "bg-red-50 text-red-700"
                      }`}
                    >
                      Errors Only ({preview.invalid_rows})
                    </button>
                  )}
                  {preview.db_existing_skus_count > 0 && (
                    <button
                      onClick={() => setPreviewFilter("existing")}
                      className={`px-2.5 py-1 rounded-lg text-[10px] font-bold transition ${
                        previewFilter === "existing" ? "bg-amber-600 text-white" : "bg-amber-50 text-amber-700"
                      }`}
                    >
                      Existing ({preview.db_existing_skus_count})
                    </button>
                  )}
                  <button
                    onClick={() => setPreviewFilter("new")}
                    className={`px-2.5 py-1 rounded-lg text-[10px] font-bold transition ${
                      previewFilter === "new" ? "bg-purple-600 text-white" : "bg-purple-50 text-purple-700"
                    }`}
                  >
                    New ({preview.new_skus_count})
                  </button>
                </div>

                <button
                  onClick={() => setStep("upload")}
                  className="inline-flex items-center space-x-1 text-[11px] font-bold text-slate-500 hover:text-slate-800"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  <span>Choose Another File</span>
                </button>
              </div>

              {/* Preview Table */}
              <div className="border border-slate-200 rounded-xl overflow-hidden max-h-80 overflow-y-auto">
                <table className="w-full text-left text-[11px]">
                  <thead className="bg-slate-900 text-white uppercase text-[9px] font-bold sticky top-0 z-10">
                    <tr>
                      <th className="py-2 px-2 text-center w-8">#</th>
                      <th className="py-2 px-2">Status</th>
                      <th className="py-2 px-2 font-mono">SKU</th>
                      <th className="py-2 px-3">Product Name</th>
                      <th className="py-2 px-2">Category</th>
                      <th className="py-2 px-2 text-right">Price (₹)</th>
                      <th className="py-2 px-2">Validation / Changes</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {filteredPreviewRows.map((r) => (
                      <tr
                        key={r.row_idx}
                        className={`hover:bg-slate-50/80 transition ${
                          !r.is_valid
                            ? "bg-red-50/40"
                            : r.is_existing_in_db
                            ? "bg-amber-50/30"
                            : ""
                        }`}
                      >
                        <td className="py-2 px-2 text-center font-bold text-slate-400">{r.row_idx}</td>
                        <td className="py-2 px-2 whitespace-nowrap">
                          {!r.is_valid ? (
                            <span className="inline-flex items-center space-x-1 px-1.5 py-0.5 rounded bg-red-100 text-red-700 font-bold text-[9px]">
                              <XCircle className="w-2.5 h-2.5" />
                              <span>Error</span>
                            </span>
                          ) : r.is_existing_in_db ? (
                            <span className="inline-flex items-center space-x-1 px-1.5 py-0.5 rounded bg-amber-100 text-amber-800 font-bold text-[9px]">
                              <span>Existing</span>
                            </span>
                          ) : (
                            <span className="inline-flex items-center space-x-1 px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-700 font-bold text-[9px]">
                              <CheckCircle className="w-2.5 h-2.5" />
                              <span>New</span>
                            </span>
                          )}
                        </td>
                        <td className="py-2 px-2 font-mono font-bold text-slate-900">{r.sku}</td>
                        <td className="py-2 px-3 font-semibold text-slate-800">{r.product_name}</td>
                        <td className="py-2 px-2 text-slate-600">{r.category}</td>
                        <td className="py-2 px-2 text-right font-black text-slate-900">
                          {formatCurrency(r.unit_price)}
                        </td>
                        <td className="py-2 px-2">
                          {r.errors.length > 0 ? (
                            <div className="space-y-0.5 text-red-600 text-[10px] font-semibold">
                              {r.errors.map((e, idx) => (
                                <div key={idx}>&bull; {e}</div>
                              ))}
                            </div>
                          ) : r.diff && Object.keys(r.diff).length > 0 ? (
                            <div className="text-[10px] text-amber-700 font-semibold space-y-0.5">
                              {Object.entries(r.diff).map(([k, v]) => (
                                <div key={k}>
                                  <span className="uppercase text-[9px] text-slate-400">{k}:</span>{" "}
                                  <span className="line-through text-slate-400">{String(v.old)}</span> &rarr;{" "}
                                  <span className="text-amber-900 font-bold">{String(v.new)}</span>
                                </div>
                              ))}
                            </div>
                          ) : (
                            <span className="text-[10px] text-emerald-600 font-bold">Ready</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* STEP 3: Final Execution Result */}
          {step === "result" && result && (
            <div className="space-y-5 text-center py-6">
              <div className="w-14 h-14 rounded-full bg-emerald-100 text-emerald-600 mx-auto flex items-center justify-center">
                <CheckCircle className="w-8 h-8" />
              </div>
              <div>
                <h3 className="text-lg font-black text-slate-900 tracking-tight">Product Import Successful</h3>
                <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">{result.message}</p>
              </div>

              <div className="grid grid-cols-4 gap-2 max-w-lg mx-auto text-center">
                <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl">
                  <div className="text-base font-black text-slate-900">{result.total_rows}</div>
                  <div className="text-[9px] font-bold text-slate-400 uppercase">Total</div>
                </div>
                <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl">
                  <div className="text-base font-black text-emerald-700">{result.inserted_count}</div>
                  <div className="text-[9px] font-bold text-emerald-600 uppercase">Inserted</div>
                </div>
                <div className="p-3 bg-blue-50 border border-blue-200 rounded-xl">
                  <div className="text-base font-black text-blue-700">{result.updated_count}</div>
                  <div className="text-[9px] font-bold text-blue-600 uppercase">Updated</div>
                </div>
                <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl">
                  <div className="text-base font-black text-amber-700">{result.skipped_count}</div>
                  <div className="text-[9px] font-bold text-amber-600 uppercase">Skipped</div>
                </div>
              </div>

              <div className="flex items-center justify-center space-x-3 pt-3">
                <button
                  onClick={handleDownloadBatchReport}
                  className="px-4 py-2 border border-slate-200 rounded-lg text-xs font-bold text-slate-700 hover:bg-slate-50 flex items-center space-x-1.5 transition"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>Download Audit Report</span>
                </button>
                <button
                  onClick={() => {
                    onSuccess();
                    onClose();
                  }}
                  className="px-5 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-xs font-bold shadow-md shadow-red-600/30 transition"
                >
                  View Updated Catalog
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 sm:p-5 border-t border-slate-200 bg-slate-50 flex items-center justify-between shrink-0">
          {step === "upload" && (
            <>
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 border border-slate-200 rounded-lg text-xs font-semibold text-slate-600 hover:bg-slate-100"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={!selectedFile || loading}
                onClick={handleAnalyzeFile}
                className="px-5 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-xs font-bold shadow-md shadow-red-600/30 disabled:opacity-50 flex items-center space-x-1.5"
              >
                {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <ArrowRight className="w-3.5 h-3.5" />}
                <span>{loading ? "Analyzing..." : "Analyze & Preview"}</span>
              </button>
            </>
          )}

          {step === "preview" && (
            <>
              <button
                type="button"
                onClick={() => setStep("upload")}
                className="px-4 py-2 border border-slate-200 rounded-lg text-xs font-semibold text-slate-600 hover:bg-slate-100"
              >
                Back to Upload
              </button>
              <button
                type="button"
                disabled={
                  !preview?.can_import ||
                  loading ||
                  (conflictPolicy === "overwrite" && !overwriteConfirmed)
                }
                onClick={handleExecuteImport}
                className="px-5 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-xs font-bold shadow-md shadow-red-600/30 disabled:opacity-50 flex items-center space-x-1.5"
              >
                {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle className="w-3.5 h-3.5" />}
                <span>
                  {loading
                    ? "Importing..."
                    : conflictPolicy === "overwrite"
                    ? "Confirm & Overwrite Import"
                    : "Confirm & Import Products"}
                </span>
              </button>
            </>
          )}

          {step === "result" && (
            <div className="w-full flex justify-end">
              <button
                type="button"
                onClick={() => {
                  onSuccess();
                  onClose();
                }}
                className="px-5 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-bold"
              >
                Done
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
