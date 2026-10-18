"use client";

import { useEffect, useState } from "react";
import {
  Package,
  Plus,
  Search,
  Filter,
  Download,
  Upload,
  Archive,
  RefreshCw,
  RotateCcw,
  Edit,
  X,
  AlertCircle,
  CheckCircle,
  History,
  FileSpreadsheet,
} from "lucide-react";
import { api } from "@/lib/api";
import { formatCurrency, formatDateTime } from "@/lib/utils";
import {
  PRODUCT_CATEGORIES,
  getProductCategoryImage,
  getProductCategoryLabel,
} from "@/lib/productCategories";
import { ProductImportModal } from "@/components/admin/ProductImportModal";

interface Product {
  id: string;
  sku: string;
  name: string;
  brand: string;
  category: string;
  category_display?: string;
  description: string;
  image_url?: string | null;
  base_price: number;
  tax_category: string;
  is_active: boolean;
}

interface ImportBatch {
  id: string;
  filename: string;
  file_type: string;
  conflict_policy: string;
  total_rows: number;
  inserted_count: number;
  updated_count: number;
  skipped_count: number;
  rejected_count: number;
  status: string;
  imported_by_email?: string;
  created_at: string;
}

export default function AdminProductsPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  // Tab State
  const [activeTab, setActiveTab] = useState<"catalog" | "history">("catalog");
  const [importBatches, setImportBatches] = useState<ImportBatch[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [importModalOpen, setImportModalOpen] = useState(false);

  // Modal State
  const [modalOpen, setModalOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState<Product | null>(null);
  const [formData, setFormData] = useState({
    sku: "",
    name: "",
    brand: "Livguard",
    category: "lithium_battery",
    description: "",
    base_price: "",
    is_active: true,
  });
  const [modalError, setModalError] = useState<string | null>(null);
  const [modalLoading, setModalLoading] = useState(false);

  const fetchProducts = async () => {
    try {
      setLoading(true);
      let url = "/admin/products?";
      if (search) url += `search=${encodeURIComponent(search)}&`;
      if (categoryFilter) url += `category=${encodeURIComponent(categoryFilter)}&`;
      if (statusFilter === "active") url += `is_active=true&`;
      if (statusFilter === "archived") url += `is_active=false&`;

      const data = await api.get<Product[]>(url);
      setProducts(data);
    } catch (err: any) {
      console.error("Error fetching products:", err);
    } finally {
      setLoading(false);
    }
  };

  const fetchImportHistory = async () => {
    try {
      setHistoryLoading(true);
      const data = await api.get<ImportBatch[]>("/admin/products/import/history");
      setImportBatches(data);
    } catch (err: any) {
      console.error("Error fetching import history:", err);
    } finally {
      setHistoryLoading(false);
    }
  };

  useEffect(() => {
    fetchProducts();
  }, [categoryFilter, statusFilter]);

  useEffect(() => {
    if (activeTab === "history") {
      fetchImportHistory();
    }
  }, [activeTab]);

  const handleDownloadBatchReport = async (batchId: string) => {
    try {
      await api.download(
        `/admin/products/import/history/${batchId}/errors.csv`,
        `Livguard_Import_Report_${batchId}.csv`
      );
    } catch (err: any) {
      alert("Failed to download audit report.");
    }
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchProducts();
  };

  const openCreateModal = () => {
    setEditingProduct(null);
    setFormData({
      sku: "",
      name: "",
      brand: "Livguard",
      category: "lithium_battery",
      description: "",
      base_price: "",
      is_active: true,
    });
    setModalError(null);
    setModalOpen(true);
  };

  const openEditModal = (p: Product) => {
    setEditingProduct(p);
    setFormData({
      sku: p.sku,
      name: p.name,
      brand: p.brand,
      category: p.category,
      description: p.description || "",
      base_price: String(p.base_price),
      is_active: p.is_active,
    });
    setModalError(null);
    setModalOpen(true);
  };

  const handleModalSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setModalError(null);
    setModalLoading(true);

    try {
      if (editingProduct) {
        await api.put(`/admin/products/${editingProduct.id}`, {
          sku: formData.sku,
          name: formData.name,
          brand: formData.brand,
          category: formData.category,
          description: formData.description,
          base_price: parseFloat(formData.base_price),
          is_active: formData.is_active,
        });
      } else {
        await api.post("/admin/products", {
          sku: formData.sku,
          name: formData.name,
          brand: formData.brand,
          category: formData.category,
          description: formData.description,
          base_price: parseFloat(formData.base_price),
          is_active: formData.is_active,
        });
      }
      setModalOpen(false);
      fetchProducts();
    } catch (err: any) {
      setModalError(err.message || "Failed to save product.");
    } finally {
      setModalLoading(false);
    }
  };

  const toggleArchive = async (p: Product) => {
    if (p.is_active) {
      if (confirm(`Archive product '${p.name}' (${p.sku})? It will not be available in new quotations.`)) {
        await api.delete(`/admin/products/${p.id}`);
        fetchProducts();
      }
    } else {
      await api.post(`/admin/products/${p.id}/restore`);
      fetchProducts();
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight">Product Master</h1>
          <p className="text-xs text-slate-500 mt-1">
            Manage SKU catalogs, unit pricing, specifications and active status
          </p>
        </div>
        <div className="flex items-center space-x-2.5">
          <a
            href="/api/v1/admin/products/export/csv"
            className="px-3.5 py-2 rounded-lg bg-white border border-slate-200 text-xs font-semibold text-slate-700 hover:bg-slate-50 flex items-center space-x-1.5 transition shadow-sm"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export CSV</span>
          </a>
          <button
            onClick={() => setImportModalOpen(true)}
            className="px-3.5 py-2 rounded-lg bg-white border border-slate-200 text-xs font-bold text-slate-800 hover:bg-slate-50 hover:border-slate-300 flex items-center space-x-1.5 transition shadow-sm"
          >
            <Upload className="w-3.5 h-3.5 text-red-600" />
            <span>Import Products</span>
          </button>
          <button
            onClick={openCreateModal}
            className="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-700 text-white text-xs font-bold flex items-center space-x-1.5 transition shadow-md shadow-red-600/20"
          >
            <Plus className="w-4 h-4" />
            <span>Add Product</span>
          </button>
        </div>
      </div>

      {/* Sub-Navigation Tabs */}
      <div className="flex items-center space-x-2 border-b border-slate-200 pb-2">
        <button
          onClick={() => setActiveTab("catalog")}
          className={`px-3 py-1.5 rounded-lg text-xs font-bold flex items-center space-x-1.5 transition ${
            activeTab === "catalog"
              ? "bg-slate-900 text-white shadow-sm"
              : "bg-white text-slate-600 hover:bg-slate-100 border border-slate-200"
          }`}
        >
          <Package className="w-3.5 h-3.5" />
          <span>Product Catalog</span>
          <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] bg-slate-200 text-slate-700">
            {products.length}
          </span>
        </button>

        <button
          onClick={() => setActiveTab("history")}
          className={`px-3 py-1.5 rounded-lg text-xs font-bold flex items-center space-x-1.5 transition ${
            activeTab === "history"
              ? "bg-slate-900 text-white shadow-sm"
              : "bg-white text-slate-600 hover:bg-slate-100 border border-slate-200"
          }`}
        >
          <History className="w-3.5 h-3.5 text-red-500" />
          <span>Import History</span>
          {importBatches.length > 0 && (
            <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] bg-slate-200 text-slate-700">
              {importBatches.length}
            </span>
          )}
        </button>
      </div>

      {activeTab === "catalog" ? (
        <>
          {/* Filter Toolbar */}
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row items-center gap-3">
            <form onSubmit={handleSearchSubmit} className="flex-1 w-full relative">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
              <input
                type="text"
                placeholder="Search by SKU, model or product name..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-9 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-red-500 focus:bg-white transition"
              />
            </form>

            <div className="flex items-center space-x-2.5 w-full md:w-auto">
              <select
                value={categoryFilter}
                onChange={(e) => setCategoryFilter(e.target.value)}
                className="bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-red-500"
              >
                <option value="">All Categories</option>
                {PRODUCT_CATEGORIES.map((cat) => (
                  <option key={cat.id} value={cat.id}>
                    {cat.label}
                  </option>
                ))}
              </select>

              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-red-500"
              >
                <option value="all">All Status</option>
                <option value="active">Active Only</option>
                <option value="archived">Archived Only</option>
              </select>
            </div>
          </div>

          {/* Products Table */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase tracking-wider text-[10px] font-bold">
                  <tr>
                    <th className="py-3 px-4 w-16">Image</th>
                    <th className="py-3 px-4">SKU / Model</th>
                    <th className="py-3 px-4">Product Name</th>
                    <th className="py-3 px-4">Category</th>
                    <th className="py-3 px-4">Master Unit Price</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {loading ? (
                    <tr>
                      <td colSpan={7} className="py-8 text-center text-slate-400">
                        Loading products catalog...
                      </td>
                    </tr>
                  ) : products.length > 0 ? (
                    products.map((p) => (
                      <tr key={p.id} className="hover:bg-slate-50/80 transition">
                        <td className="py-3 px-4">
                          <div className="w-12 h-12 bg-white rounded-lg border border-slate-200 p-1 flex items-center justify-center overflow-hidden shrink-0">
                            <img
                              src={getProductCategoryImage(p.category, p.image_url)}
                              alt={p.name}
                              className="w-full h-full object-contain"
                            />
                          </div>
                        </td>
                        <td className="py-3.5 px-4 font-mono font-bold text-red-600">{p.sku}</td>
                        <td className="py-3.5 px-4 font-bold text-slate-900">
                          <div>{p.name}</div>
                          <div className="text-[11px] text-slate-400 font-normal line-clamp-1">
                            {p.description || "No description"}
                          </div>
                        </td>
                        <td className="py-3.5 px-4">
                          <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-semibold text-[10px]">
                            {getProductCategoryLabel(p.category)}
                          </span>
                        </td>
                        <td className="py-3.5 px-4 font-black text-slate-900">{formatCurrency(p.base_price)}</td>
                        <td className="py-3.5 px-4">
                          {p.is_active ? (
                            <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 text-[10px] font-bold">
                              <CheckCircle className="w-3 h-3 text-emerald-500" />
                              <span>Active</span>
                            </span>
                          ) : (
                            <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full bg-slate-100 text-slate-500 text-[10px] font-bold">
                              <Archive className="w-3 h-3 text-slate-400" />
                              <span>Archived</span>
                            </span>
                          )}
                        </td>
                        <td className="py-3.5 px-4 text-right">
                          <div className="inline-flex items-center space-x-2">
                            <button
                              onClick={() => openEditModal(p)}
                              className="p-1 rounded text-slate-400 hover:text-slate-800 hover:bg-slate-100 transition"
                              title="Edit Product"
                            >
                              <Edit className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => toggleArchive(p)}
                              className={`p-1 rounded transition ${
                                p.is_active
                                  ? "text-slate-400 hover:text-red-600 hover:bg-red-50"
                                  : "text-slate-400 hover:text-emerald-600 hover:bg-emerald-50"
                              }`}
                              title={p.is_active ? "Archive Product" : "Restore Product"}
                            >
                              {p.is_active ? <Archive className="w-4 h-4" /> : <RotateCcw className="w-4 h-4" />}
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={7} className="py-8 text-center text-slate-400">
                        No products found matching filters.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
      ) : (
        /* Import History Table */
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden space-y-4 p-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-black text-slate-900 tracking-tight">Bulk Import Batch History</h2>
              <p className="text-[11px] text-slate-500 mt-0.5">
                Audit trail of past product batch uploads, conflict policies, and outcome reports
              </p>
            </div>
            <button
              onClick={fetchImportHistory}
              className="px-3 py-1.5 rounded-lg border border-slate-200 text-xs font-semibold text-slate-700 hover:bg-slate-50 flex items-center space-x-1.5 transition"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${historyLoading ? "animate-spin" : ""}`} />
              <span>Refresh</span>
            </button>
          </div>

          <div className="overflow-x-auto border border-slate-200 rounded-xl">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase tracking-wider text-[10px] font-bold">
                <tr>
                  <th className="py-3 px-4">Batch ID</th>
                  <th className="py-3 px-4">Filename</th>
                  <th className="py-3 px-4">Policy</th>
                  <th className="py-3 px-4 text-center">Total</th>
                  <th className="py-3 px-4 text-center">Inserted</th>
                  <th className="py-3 px-4 text-center">Updated</th>
                  <th className="py-3 px-4 text-center">Skipped</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Imported By & Date</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {historyLoading ? (
                  <tr>
                    <td colSpan={10} className="py-8 text-center text-slate-400">
                      Loading import history...
                    </td>
                  </tr>
                ) : importBatches.length > 0 ? (
                  importBatches.map((b) => (
                    <tr key={b.id} className="hover:bg-slate-50/80 transition">
                      <td className="py-3.5 px-4 font-mono font-bold text-slate-900 text-[10.5px]">
                        {b.id.slice(0, 8)}...
                      </td>
                      <td className="py-3.5 px-4 font-semibold text-slate-800">
                        <div className="flex items-center space-x-1.5">
                          <FileSpreadsheet className="w-4 h-4 text-emerald-600 shrink-0" />
                          <span className="truncate max-w-[150px]">{b.filename}</span>
                          <span className="uppercase text-[9px] px-1.5 py-0.2 rounded bg-slate-100 text-slate-600 font-bold">
                            {b.file_type}
                          </span>
                        </div>
                      </td>
                      <td className="py-3.5 px-4">
                        <span
                          className={`px-2 py-0.5 rounded font-bold text-[10px] uppercase ${
                            b.conflict_policy === "overwrite"
                              ? "bg-red-50 text-red-700"
                              : "bg-slate-100 text-slate-700"
                          }`}
                        >
                          {b.conflict_policy}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-center font-bold text-slate-900">{b.total_rows}</td>
                      <td className="py-3.5 px-4 text-center font-bold text-emerald-600">{b.inserted_count}</td>
                      <td className="py-3.5 px-4 text-center font-bold text-blue-600">{b.updated_count}</td>
                      <td className="py-3.5 px-4 text-center font-bold text-amber-600">{b.skipped_count}</td>
                      <td className="py-3.5 px-4">
                        <span
                          className={`inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-[10px] font-bold ${
                            b.status === "COMPLETED"
                              ? "bg-emerald-50 text-emerald-700"
                              : "bg-red-50 text-red-700"
                          }`}
                        >
                          <span>{b.status}</span>
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-[11px] text-slate-600">
                        <div>{b.imported_by_email || "Admin"}</div>
                        <div className="text-[10px] text-slate-400">{formatDateTime(b.created_at)}</div>
                      </td>
                      <td className="py-3.5 px-4 text-right">
                        <button
                          onClick={() => handleDownloadBatchReport(b.id)}
                          className="px-2.5 py-1 rounded bg-white border border-slate-200 text-slate-700 hover:bg-slate-50 text-[11px] font-bold inline-flex items-center space-x-1 shadow-sm transition"
                          title="Download row-level outcome report"
                        >
                          <Download className="w-3 h-3 text-red-600" />
                          <span>Audit CSV</span>
                        </button>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={10} className="py-8 text-center text-slate-400">
                      No bulk product imports recorded yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Product Add/Edit Modal */}
      {modalOpen && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-lg w-full p-6 relative">
            <button
              onClick={() => setModalOpen(false)}
              className="absolute top-5 right-5 text-slate-400 hover:text-slate-700"
            >
              <X className="w-5 h-5" />
            </button>

            <h3 className="text-lg font-black text-slate-900 tracking-tight">
              {editingProduct ? "Edit Product Master" : "Add New Livguard Product"}
            </h3>
            <p className="text-xs text-slate-500 mt-1">
              {editingProduct
                ? "Updating SKU or base price will affect subsequent quotations."
                : "Create an active SKU entry in Livguard master catalog."}
            </p>

            {modalError && (
              <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center space-x-2 text-xs text-red-700">
                <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
                <span>{modalError}</span>
              </div>
            )}

            <form onSubmit={handleModalSubmit} className="mt-5 space-y-4 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                    SKU / Model No. *
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.sku}
                    onChange={(e) => setFormData({ ...formData, sku: e.target.value.toUpperCase() })}
                    placeholder="LG-LX-100AH"
                    className="mt-1 w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg font-mono font-bold focus:ring-2 focus:ring-red-500 focus:bg-white"
                  />
                </div>
                <div>
                  <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                    Category *
                  </label>
                  <select
                    value={formData.category}
                    onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                    className="mt-1 w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg font-semibold focus:ring-2 focus:ring-red-500 focus:bg-white"
                  >
                    {PRODUCT_CATEGORIES.map((cat) => (
                      <option key={cat.id} value={cat.id}>
                        {cat.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Automatic Category Image Preview */}
              <div className="flex items-center gap-3 p-2.5 bg-slate-50 rounded-xl border border-slate-200">
                <div className="w-12 h-12 bg-white rounded-lg border border-slate-200 p-1 flex items-center justify-center overflow-hidden shrink-0">
                  <img
                    src={getProductCategoryImage(formData.category)}
                    alt="Category Asset"
                    className="w-full h-full object-contain"
                  />
                </div>
                <div>
                  <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                    Auto Assigned Product Image
                  </div>
                  <div className="text-xs font-bold text-slate-800">
                    {getProductCategoryLabel(formData.category)}
                  </div>
                  <div className="text-[10px] text-slate-400">
                    Included in quotation preview, PDF and PNG
                  </div>
                </div>
              </div>

              <div>
                <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                  Product Name *
                </label>
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="Livguard Lithium-X 100Ah / 12.8V Battery"
                  className="mt-1 w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg font-bold text-slate-900 focus:ring-2 focus:ring-red-500 focus:bg-white"
                />
              </div>

              <div>
                <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                  Master Base Price (₹) *
                </label>
                <input
                  type="number"
                  step="0.01"
                  required
                  value={formData.base_price}
                  onChange={(e) => setFormData({ ...formData, base_price: e.target.value })}
                  placeholder="34999.00"
                  className="mt-1 w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg font-black text-slate-900 focus:ring-2 focus:ring-red-500 focus:bg-white"
                />
              </div>

              <div>
                <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                  Description
                </label>
                <textarea
                  rows={3}
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Product specifications and features..."
                  className="mt-1 w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:ring-2 focus:ring-red-500 focus:bg-white"
                />
              </div>

              <div className="flex items-center space-x-2 pt-2">
                <input
                  type="checkbox"
                  id="prod_active"
                  checked={formData.is_active}
                  onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                  className="w-4 h-4 text-red-600 rounded border-slate-300 focus:ring-red-500"
                />
                <label htmlFor="prod_active" className="text-xs font-semibold text-slate-700">
                  Active for Quotations
                </label>
              </div>

              <div className="flex items-center justify-end space-x-3 pt-4 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  className="px-4 py-2 border border-slate-200 rounded-lg text-xs font-semibold text-slate-600 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={modalLoading}
                  className="px-5 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-xs font-bold shadow-md shadow-red-600/30 disabled:opacity-50"
                >
                  {modalLoading ? "Saving..." : "Save Product"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Bulk Product Import Modal */}
      <ProductImportModal
        isOpen={importModalOpen}
        onClose={() => setImportModalOpen(false)}
        onSuccess={() => {
          fetchProducts();
          fetchImportHistory();
        }}
      />
    </div>
  );
}
