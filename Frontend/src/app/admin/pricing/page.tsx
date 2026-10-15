"use client";

import { useEffect, useState } from "react";
import { Tag, Search, Edit3, History, ArrowRight, CheckCircle, AlertCircle, X } from "lucide-react";
import { api } from "@/lib/api";
import { formatCurrency, formatDateTime } from "@/lib/utils";

interface Product {
  id: string;
  sku: string;
  name: string;
  category: string;
  base_price: number;
}

interface PriceHistoryItem {
  id: string;
  old_price: number;
  new_price: number;
  reason: string;
  effective_from: string;
  created_at: string;
  changed_by: string;
}

export default function AdminPricingPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  // Update Price Modal
  const [updateModalOpen, setUpdateModalOpen] = useState(false);
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
  const [newPrice, setNewPrice] = useState("");
  const [changeReason, setChangeReason] = useState("");
  const [modalLoading, setModalLoading] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);

  // History Modal
  const [historyModalOpen, setHistoryModalOpen] = useState(false);
  const [historyList, setHistoryList] = useState<PriceHistoryItem[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  const fetchProducts = async () => {
    try {
      setLoading(true);
      const data = await api.get<Product[]>(`/admin/products?is_active=true${search ? `&search=${encodeURIComponent(search)}` : ""}`);
      setProducts(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProducts();
  }, []);

  const openUpdateModal = (p: Product) => {
    setSelectedProduct(p);
    setNewPrice(String(p.base_price));
    setChangeReason("");
    setModalError(null);
    setUpdateModalOpen(true);
  };

  const handlePriceSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedProduct) return;
    setModalError(null);
    setModalLoading(true);

    try {
      await api.put(`/admin/prices/products/${selectedProduct.id}`, {
        new_price: parseFloat(newPrice),
        reason: changeReason || "Scheduled price revision",
      });
      setUpdateModalOpen(false);
      fetchProducts();
    } catch (err: any) {
      setModalError(err.message || "Failed to update price.");
    } finally {
      setModalLoading(false);
    }
  };

  const openHistoryModal = async (p: Product) => {
    setSelectedProduct(p);
    setHistoryModalOpen(true);
    setHistoryLoading(true);
    try {
      const hist = await api.get<PriceHistoryItem[]>(`/admin/prices/products/${p.id}/history`);
      setHistoryList(hist);
    } catch (err) {
      console.error(err);
    } finally {
      setHistoryLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-black text-slate-900 tracking-tight">Price Management</h1>
        <p className="text-xs text-slate-500 mt-1">
          Authorized product base price adjustments and historical audit trails
        </p>
      </div>

      {/* Info Notice */}
      <div className="bg-slate-900 text-white p-4 rounded-xl shadow-sm text-xs flex items-center justify-between">
        <div>
          <strong className="text-red-400">Non-Negotiable Business Rule:</strong>
          <span className="text-slate-300 ml-1.5">
            Price revisions apply exclusively to new quotations. Previously issued quotations and revisions maintain their immutable snapshot prices.
          </span>
        </div>
      </div>

      {/* Search Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex items-center gap-3">
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
          <input
            type="text"
            placeholder="Search active products by SKU or name..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && fetchProducts()}
            className="w-full pl-9 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-red-500 focus:bg-white transition"
          />
        </div>
        <button
          onClick={fetchProducts}
          className="px-4 py-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-xs font-semibold text-slate-700 transition"
        >
          Search
        </button>
      </div>

      {/* Pricing Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase tracking-wider text-[10px] font-bold">
            <tr>
              <th className="py-3 px-4">SKU / Model</th>
              <th className="py-3 px-4">Product Name</th>
              <th className="py-3 px-4">Category</th>
              <th className="py-3 px-4">Current Master Price</th>
              <th className="py-3 px-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {loading ? (
              <tr>
                <td colSpan={5} className="py-8 text-center text-slate-400">
                  Loading pricing catalog...
                </td>
              </tr>
            ) : products.map((p) => (
              <tr key={p.id} className="hover:bg-slate-50/80 transition">
                <td className="py-3.5 px-4 font-mono font-bold text-red-600">{p.sku}</td>
                <td className="py-3.5 px-4 font-bold text-slate-900">{p.name}</td>
                <td className="py-3.5 px-4">
                  <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-semibold text-[10px]">
                    {p.category}
                  </span>
                </td>
                <td className="py-3.5 px-4 font-black text-slate-900">{formatCurrency(p.base_price)}</td>
                <td className="py-3.5 px-4 text-right">
                  <div className="inline-flex items-center space-x-2">
                    <button
                      onClick={() => openHistoryModal(p)}
                      className="px-2.5 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-600 font-semibold flex items-center space-x-1"
                      title="View Price History"
                    >
                      <History className="w-3.5 h-3.5 text-slate-500" />
                      <span>History</span>
                    </button>
                    <button
                      onClick={() => openUpdateModal(p)}
                      className="px-3 py-1.5 rounded-lg bg-red-600 hover:bg-red-700 text-white font-bold flex items-center space-x-1 shadow-sm"
                      title="Update Price"
                    >
                      <Edit3 className="w-3.5 h-3.5" />
                      <span>Adjust Price</span>
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Adjust Price Modal */}
      {updateModalOpen && selectedProduct && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-md w-full p-6 relative">
            <button
              onClick={() => setUpdateModalOpen(false)}
              className="absolute top-5 right-5 text-slate-400 hover:text-slate-700"
            >
              <X className="w-5 h-5" />
            </button>

            <h3 className="text-base font-black text-slate-900 tracking-tight">Adjust Product Base Price</h3>
            <p className="text-xs text-slate-500 mt-1">
              {selectedProduct.name} ({selectedProduct.sku})
            </p>

            {modalError && (
              <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center space-x-2 text-xs text-red-700">
                <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
                <span>{modalError}</span>
              </div>
            )}

            <form onSubmit={handlePriceSubmit} className="mt-5 space-y-4 text-xs">
              <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg flex justify-between items-center">
                <span className="font-semibold text-slate-600">Current Base Price:</span>
                <span className="font-black text-slate-900 text-sm">{formatCurrency(selectedProduct.base_price)}</span>
              </div>

              <div>
                <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                  New Base Price (₹) *
                </label>
                <input
                  type="number"
                  step="0.01"
                  required
                  value={newPrice}
                  onChange={(e) => setNewPrice(e.target.value)}
                  className="mt-1 w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg font-black text-sm text-slate-900 focus:ring-2 focus:ring-red-500 focus:bg-white"
                />
              </div>

              <div>
                <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                  Reason for Adjustment *
                </label>
                <textarea
                  rows={2}
                  required
                  value={changeReason}
                  onChange={(e) => setChangeReason(e.target.value)}
                  placeholder="e.g. Raw material cost update, seasonal promotion, or manufacturer tariff adjustment"
                  className="mt-1 w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:ring-2 focus:ring-red-500 focus:bg-white"
                />
              </div>

              <div className="flex items-center justify-end space-x-3 pt-4 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setUpdateModalOpen(false)}
                  className="px-4 py-2 border border-slate-200 rounded-lg text-xs font-semibold text-slate-600 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={modalLoading}
                  className="px-5 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-xs font-bold shadow-md shadow-red-600/30 disabled:opacity-50"
                >
                  {modalLoading ? "Saving..." : "Commit Price Change"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* History Modal */}
      {historyModalOpen && selectedProduct && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-lg w-full p-6 relative">
            <button
              onClick={() => setHistoryModalOpen(false)}
              className="absolute top-5 right-5 text-slate-400 hover:text-slate-700"
            >
              <X className="w-5 h-5" />
            </button>

            <h3 className="text-base font-black text-slate-900 tracking-tight">Price Revision History</h3>
            <p className="text-xs text-slate-500 mt-1">
              Audit log for {selectedProduct.name} ({selectedProduct.sku})
            </p>

            <div className="mt-5 max-h-80 overflow-y-auto space-y-3">
              {historyLoading ? (
                <p className="text-xs text-slate-400 text-center py-6">Loading audit records...</p>
              ) : historyList.length > 0 ? (
                historyList.map((h) => (
                  <div key={h.id} className="p-3 bg-slate-50 border border-slate-200 rounded-xl text-xs space-y-1.5">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <span className="line-through text-slate-400">{formatCurrency(h.old_price)}</span>
                        <ArrowRight className="w-3.5 h-3.5 text-slate-400" />
                        <span className="font-black text-slate-900">{formatCurrency(h.new_price)}</span>
                      </div>
                      <span className="text-[10px] text-slate-400 font-medium">{formatDateTime(h.created_at)}</span>
                    </div>
                    <div className="text-slate-600">
                      <strong>Reason:</strong> {h.reason || "Manual update"}
                    </div>
                    <div className="text-[10px] text-slate-400">
                      Changed by: <strong className="text-slate-700">{h.changed_by}</strong>
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-xs text-slate-400 text-center py-6">No previous price revisions found.</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
