"use client";

import { useEffect, useState } from "react";
import { Ticket, Plus, CheckCircle, XCircle, AlertCircle, Eye, X, Percent, IndianRupee } from "lucide-react";
import { api } from "@/lib/api";
import { formatCurrency, formatDateTime } from "@/lib/utils";

interface Coupon {
  id: string;
  code: string;
  discount_type: "PERCENTAGE" | "FIXED";
  discount_value: number;
  max_discount: number | null;
  min_subtotal: number;
  usage_limit: number | null;
  used_count: number;
  is_active: boolean;
  created_at: string;
}

interface Redemption {
  id: string;
  quotation_id: string;
  agent_name: string;
  discount_granted: number;
  created_at: string;
}

export default function AdminCouponsPage() {
  const [coupons, setCoupons] = useState<Coupon[]>([]);
  const [loading, setLoading] = useState(true);

  // Create Modal
  const [createOpen, setCreateOpen] = useState(false);
  const [formData, setFormData] = useState({
    code: "",
    discount_type: "PERCENTAGE" as "PERCENTAGE" | "FIXED",
    discount_value: "",
    max_discount: "",
    min_subtotal: "0",
    usage_limit: "",
    is_active: true,
  });
  const [createLoading, setCreateLoading] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  // Redemptions Modal
  const [redemptionsOpen, setRedemptionsOpen] = useState(false);
  const [selectedCoupon, setSelectedCoupon] = useState<Coupon | null>(null);
  const [redemptions, setRedemptions] = useState<Redemption[]>([]);
  const [redemptionsLoading, setRedemptionsLoading] = useState(false);

  const fetchCoupons = async () => {
    try {
      setLoading(true);
      const data = await api.get<Coupon[]>("/admin/coupons");
      setCoupons(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCoupons();
  }, []);

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreateError(null);
    setCreateLoading(true);

    try {
      await api.post("/admin/coupons", {
        code: formData.code.toUpperCase().trim(),
        discount_type: formData.discount_type,
        discount_value: parseFloat(formData.discount_value),
        max_discount: formData.max_discount ? parseFloat(formData.max_discount) : null,
        min_subtotal: parseFloat(formData.min_subtotal || "0"),
        usage_limit: formData.usage_limit ? parseInt(formData.usage_limit) : null,
        is_active: formData.is_active,
      });
      setCreateOpen(false);
      fetchCoupons();
    } catch (err: any) {
      setCreateError(err.message || "Failed to create coupon.");
    } finally {
      setCreateLoading(false);
    }
  };

  const toggleStatus = async (c: Coupon) => {
    try {
      await api.put(`/admin/coupons/${c.id}`, { is_active: !c.is_active });
      fetchCoupons();
    } catch (err) {
      console.error(err);
    }
  };

  const viewRedemptions = async (c: Coupon) => {
    setSelectedCoupon(c);
    setRedemptionsOpen(true);
    setRedemptionsLoading(true);
    try {
      const data = await api.get<Redemption[]>(`/admin/coupons/${c.id}/redemptions`);
      setRedemptions(data);
    } catch (err) {
      console.error(err);
    } finally {
      setRedemptionsLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight">Coupon & Discount Rules</h1>
          <p className="text-xs text-slate-500 mt-1">
            Configure promotional discount codes, usage limits, and review redemption audit trails
          </p>
        </div>
        <button
          onClick={() => {
            setFormData({
              code: "",
              discount_type: "PERCENTAGE",
              discount_value: "",
              max_discount: "",
              min_subtotal: "0",
              usage_limit: "",
              is_active: true,
            });
            setCreateError(null);
            setCreateOpen(true);
          }}
          className="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-700 text-white text-xs font-bold flex items-center space-x-1.5 transition shadow-md shadow-red-600/20"
        >
          <Plus className="w-4 h-4" />
          <span>Create Coupon</span>
        </button>
      </div>

      {/* Coupons Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase tracking-wider text-[10px] font-bold">
              <tr>
                <th className="py-3 px-4">Coupon Code</th>
                <th className="py-3 px-4">Discount Type & Value</th>
                <th className="py-3 px-4">Min. Subtotal</th>
                <th className="py-3 px-4">Max Cap</th>
                <th className="py-3 px-4">Usage / Limit</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-400">
                    Loading promotional coupons...
                  </td>
                </tr>
              ) : coupons.length > 0 ? (
                coupons.map((c) => (
                  <tr key={c.id} className="hover:bg-slate-50/80 transition">
                    <td className="py-3.5 px-4 font-mono font-black text-red-600 text-sm">{c.code}</td>
                    <td className="py-3.5 px-4 font-bold text-slate-900">
                      {c.discount_type === "PERCENTAGE" ? (
                        <span className="flex items-center space-x-1">
                          <Percent className="w-3.5 h-3.5 text-blue-600" />
                          <span>{c.discount_value}% Off</span>
                        </span>
                      ) : (
                        <span className="flex items-center space-x-1">
                          <IndianRupee className="w-3.5 h-3.5 text-emerald-600" />
                          <span>{formatCurrency(c.discount_value)} Flat Off</span>
                        </span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 text-slate-600 font-semibold">{formatCurrency(c.min_subtotal)}</td>
                    <td className="py-3.5 px-4 text-slate-600 font-semibold">
                      {c.max_discount ? formatCurrency(c.max_discount) : "No Cap"}
                    </td>
                    <td className="py-3.5 px-4 font-bold text-slate-700">
                      <span>{c.used_count}</span>
                      <span className="text-slate-400"> / {c.usage_limit ?? "Unlimited"}</span>
                    </td>
                    <td className="py-3.5 px-4">
                      {c.is_active ? (
                        <span className="px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 font-bold text-[10px]">
                          Active
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded-full bg-slate-100 text-slate-500 font-bold text-[10px]">
                          Inactive
                        </span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <div className="inline-flex items-center space-x-2">
                        <button
                          onClick={() => viewRedemptions(c)}
                          className="px-2.5 py-1 rounded-md border border-slate-200 hover:bg-slate-50 text-slate-600 font-semibold flex items-center space-x-1"
                        >
                          <Eye className="w-3.5 h-3.5" />
                          <span>Redemptions ({c.used_count})</span>
                        </button>
                        <button
                          onClick={() => toggleStatus(c)}
                          className={`px-2.5 py-1 rounded-md font-semibold text-[11px] ${
                            c.is_active
                              ? "bg-slate-100 hover:bg-slate-200 text-slate-700"
                              : "bg-emerald-50 hover:bg-emerald-100 text-emerald-700"
                          }`}
                        >
                          {c.is_active ? "Deactivate" : "Activate"}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-400">
                    No active promotional coupons defined.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Create Modal */}
      {createOpen && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-md w-full p-6 relative">
            <button
              onClick={() => setCreateOpen(false)}
              className="absolute top-5 right-5 text-slate-400 hover:text-slate-700"
            >
              <X className="w-5 h-5" />
            </button>

            <h3 className="text-base font-black text-slate-900 tracking-tight">Create Promotional Coupon</h3>
            <p className="text-xs text-slate-500 mt-1">Configure discount rates and validation thresholds.</p>

            {createError && (
              <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center space-x-2 text-xs text-red-700">
                <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
                <span>{createError}</span>
              </div>
            )}

            <form onSubmit={handleCreateSubmit} className="mt-5 space-y-4 text-xs">
              <div>
                <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                  Coupon Code *
                </label>
                <input
                  type="text"
                  required
                  value={formData.code}
                  onChange={(e) => setFormData({ ...formData, code: e.target.value.toUpperCase() })}
                  placeholder="LIVGUARD10"
                  className="mt-1 w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg font-mono font-black text-sm tracking-wider focus:ring-2 focus:ring-red-500 focus:bg-white"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                    Discount Type *
                  </label>
                  <select
                    value={formData.discount_type}
                    onChange={(e) =>
                      setFormData({ ...formData, discount_type: e.target.value as "PERCENTAGE" | "FIXED" })
                    }
                    className="mt-1 w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg font-semibold focus:ring-2 focus:ring-red-500 focus:bg-white"
                  >
                    <option value="PERCENTAGE">Percentage (%)</option>
                    <option value="FIXED">Fixed Amount (₹)</option>
                  </select>
                </div>
                <div>
                  <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                    Discount Value *
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    required
                    value={formData.discount_value}
                    onChange={(e) => setFormData({ ...formData, discount_value: e.target.value })}
                    placeholder={formData.discount_type === "PERCENTAGE" ? "10" : "1500"}
                    className="mt-1 w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg font-black focus:ring-2 focus:ring-red-500 focus:bg-white"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                    Min. Subtotal (₹)
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    value={formData.min_subtotal}
                    onChange={(e) => setFormData({ ...formData, min_subtotal: e.target.value })}
                    placeholder="20000"
                    className="mt-1 w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:ring-2 focus:ring-red-500 focus:bg-white"
                  />
                </div>
                <div>
                  <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                    Max Cap (₹)
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    value={formData.max_discount}
                    onChange={(e) => setFormData({ ...formData, max_discount: e.target.value })}
                    placeholder="5000"
                    className="mt-1 w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:ring-2 focus:ring-red-500 focus:bg-white"
                  />
                </div>
              </div>

              <div>
                <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                  Total Usage Limit (Optional)
                </label>
                <input
                  type="number"
                  value={formData.usage_limit}
                  onChange={(e) => setFormData({ ...formData, usage_limit: e.target.value })}
                  placeholder="Leave empty for unlimited redemptions"
                  className="mt-1 w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:ring-2 focus:ring-red-500 focus:bg-white"
                />
              </div>

              <div className="flex items-center space-x-2 pt-2">
                <input
                  type="checkbox"
                  id="coupon_active"
                  checked={formData.is_active}
                  onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                  className="w-4 h-4 text-red-600 rounded border-slate-300 focus:ring-red-500"
                />
                <label htmlFor="coupon_active" className="text-xs font-semibold text-slate-700">
                  Active for Quotations Immediately
                </label>
              </div>

              <div className="flex items-center justify-end space-x-3 pt-4 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setCreateOpen(false)}
                  className="px-4 py-2 border border-slate-200 rounded-lg text-xs font-semibold text-slate-600 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createLoading}
                  className="px-5 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-xs font-bold shadow-md shadow-red-600/30 disabled:opacity-50"
                >
                  {createLoading ? "Creating..." : "Save Coupon"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Redemptions Modal */}
      {redemptionsOpen && selectedCoupon && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-lg w-full p-6 relative">
            <button
              onClick={() => setRedemptionsOpen(false)}
              className="absolute top-5 right-5 text-slate-400 hover:text-slate-700"
            >
              <X className="w-5 h-5" />
            </button>

            <h3 className="text-base font-black text-slate-900 tracking-tight">Coupon Redemptions</h3>
            <p className="text-xs text-slate-500 mt-1">Audit log for coupon code {selectedCoupon.code}</p>

            <div className="mt-5 max-h-80 overflow-y-auto space-y-2.5">
              {redemptionsLoading ? (
                <p className="text-xs text-slate-400 text-center py-6">Loading redemptions...</p>
              ) : redemptions.length > 0 ? (
                redemptions.map((r) => (
                  <div
                    key={r.id}
                    className="p-3 bg-slate-50 border border-slate-200 rounded-xl text-xs flex items-center justify-between"
                  >
                    <div>
                      <div className="font-bold text-slate-900">{r.agent_name}</div>
                      <div className="text-[10px] text-slate-400 mt-0.5">{formatDateTime(r.created_at)}</div>
                    </div>
                    <div className="text-right">
                      <div className="font-black text-emerald-600">-{formatCurrency(r.discount_granted)}</div>
                      <div className="text-[10px] text-slate-400 font-mono">Quote ID: {r.quotation_id.slice(0, 8)}...</div>
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-xs text-slate-400 text-center py-6">No redemptions recorded for this coupon yet.</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
