"use client";

import { useEffect, useState } from "react";
import {
  Users,
  UserPlus,
  Search,
  CheckCircle2,
  XCircle,
  Key,
  History,
  Activity,
  AlertCircle,
  X,
  Phone,
  Mail,
} from "lucide-react";
import { api } from "@/lib/api";
import { formatDateTime } from "@/lib/utils";

interface Agent {
  id: string;
  email: string;
  full_name: string;
  mobile: string;
  is_active: boolean;
  is_online: boolean;
  last_active_at: string | null;
  created_at: string;
  total_quotations: number;
  confirmed_orders: number;
  conversion_rate: number;
}

interface LoginLog {
  id: string;
  ip_address: string;
  user_agent: string;
  status: string;
  created_at: string;
}

export default function AdminAgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  // Create Modal
  const [createOpen, setCreateOpen] = useState(false);
  const [createForm, setCreateForm] = useState({
    email: "",
    password: "",
    full_name: "",
    mobile: "",
  });
  const [createLoading, setCreateLoading] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  // Password Reset Modal
  const [resetOpen, setResetOpen] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [newPassword, setNewPassword] = useState("");
  const [resetLoading, setResetLoading] = useState(false);

  // Login History Modal
  const [historyOpen, setHistoryOpen] = useState(false);
  const [historyLogs, setHistoryLogs] = useState<LoginLog[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  const fetchAgents = async () => {
    try {
      setLoading(true);
      const data = await api.get<Agent[]>(`/admin/users/agents${search ? `?search=${encodeURIComponent(search)}` : ""}`);
      setAgents(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAgents();
  }, []);

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreateError(null);
    setCreateLoading(true);

    try {
      await api.post("/admin/users/agents", {
        email: createForm.email,
        password: createForm.password,
        full_name: createForm.full_name,
        mobile: createForm.mobile,
      });
      setCreateOpen(false);
      fetchAgents();
    } catch (err: any) {
      setCreateError(err.message || "Failed to create agent");
    } finally {
      setCreateLoading(false);
    }
  };

  const toggleAgentStatus = async (agent: Agent) => {
    if (confirm(`Change status for agent ${agent.full_name} to ${agent.is_active ? "Inactive" : "Active"}?`)) {
      await api.put(`/admin/users/agents/${agent.id}`, { is_active: !agent.is_active });
      fetchAgents();
    }
  };

  const handlePasswordReset = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedAgent) return;
    setResetLoading(true);

    try {
      await api.post(`/admin/users/agents/${selectedAgent.id}/reset-password`, {
        new_password: newPassword,
      });
      alert(`Password successfully updated for ${selectedAgent.full_name}`);
      setResetOpen(false);
      setNewPassword("");
    } catch (err: any) {
      alert(err.message || "Failed to reset password");
    } finally {
      setResetLoading(false);
    }
  };

  const openHistory = async (agent: Agent) => {
    setSelectedAgent(agent);
    setHistoryOpen(true);
    setHistoryLoading(true);
    try {
      const logs = await api.get<LoginLog[]>(`/admin/users/agents/${agent.id}/login-history`);
      setHistoryLogs(logs);
    } catch (err) {
      console.error(err);
    } finally {
      setHistoryLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight">Agent Personnel Management</h1>
          <p className="text-xs text-slate-500 mt-1">
            Manage authorized field agents, monitor real-time presence, and audit conversion metrics
          </p>
        </div>
        <button
          onClick={() => {
            setCreateForm({ email: "", password: "", full_name: "", mobile: "" });
            setCreateError(null);
            setCreateOpen(true);
          }}
          className="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-700 text-white text-xs font-bold flex items-center space-x-1.5 transition shadow-md shadow-red-600/20"
        >
          <UserPlus className="w-4 h-4" />
          <span>Add New Agent</span>
        </button>
      </div>

      {/* Search Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex items-center gap-3">
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
          <input
            type="text"
            placeholder="Search agents by name, email or mobile..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && fetchAgents()}
            className="w-full pl-9 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-red-500 focus:bg-white transition"
          />
        </div>
        <button
          onClick={fetchAgents}
          className="px-4 py-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-xs font-semibold text-slate-700 transition"
        >
          Search
        </button>
      </div>

      {/* Agents Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase tracking-wider text-[10px] font-bold">
              <tr>
                <th className="py-3 px-4">Agent Name & Presence</th>
                <th className="py-3 px-4">Contact Info</th>
                <th className="py-3 px-4">Quotes Generated</th>
                <th className="py-3 px-4">Orders Confirmed</th>
                <th className="py-3 px-4">Conversion</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-400">
                    Loading agent personnel...
                  </td>
                </tr>
              ) : agents.length > 0 ? (
                agents.map((ag) => (
                  <tr key={ag.id} className="hover:bg-slate-50/80 transition">
                    <td className="py-3.5 px-4">
                      <div className="flex items-center space-x-2">
                        <span
                          className={`w-2.5 h-2.5 rounded-full shrink-0 ${
                            ag.is_online ? "bg-emerald-500 animate-pulse" : "bg-slate-300"
                          }`}
                          title={ag.is_online ? "Active within 5 minutes" : "Offline"}
                        />
                        <div>
                          <div className="font-bold text-slate-900">{ag.full_name}</div>
                          <div className="text-[10px] text-slate-400">
                            {ag.is_online ? "Online Now" : `Last seen: ${ag.last_active_at ? formatDateTime(ag.last_active_at) : "Never"}`}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="py-3.5 px-4 text-slate-600">
                      <div className="flex items-center space-x-1.5">
                        <Mail className="w-3 h-3 text-slate-400 shrink-0" />
                        <span>{ag.email}</span>
                      </div>
                      <div className="flex items-center space-x-1.5 mt-0.5">
                        <Phone className="w-3 h-3 text-slate-400 shrink-0" />
                        <span>{ag.mobile || "N/A"}</span>
                      </div>
                    </td>
                    <td className="py-3.5 px-4 font-bold text-slate-800">{ag.total_quotations}</td>
                    <td className="py-3.5 px-4 font-bold text-emerald-600">{ag.confirmed_orders}</td>
                    <td className="py-3.5 px-4 font-black text-slate-900">{ag.conversion_rate}%</td>
                    <td className="py-3.5 px-4">
                      {ag.is_active ? (
                        <span className="px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 font-bold text-[10px]">
                          Active
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded-full bg-red-50 text-red-700 font-bold text-[10px]">
                          Deactivated
                        </span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <div className="inline-flex items-center space-x-2">
                        <button
                          onClick={() => openHistory(ag)}
                          className="p-1 rounded text-slate-400 hover:text-slate-800 hover:bg-slate-100"
                          title="View Login History"
                        >
                          <History className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => {
                            setSelectedAgent(ag);
                            setResetOpen(true);
                          }}
                          className="p-1 rounded text-slate-400 hover:text-blue-600 hover:bg-blue-50"
                          title="Reset Password"
                        >
                          <Key className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => toggleAgentStatus(ag)}
                          className={`px-2 py-1 rounded text-[10px] font-bold transition ${
                            ag.is_active
                              ? "bg-slate-100 hover:bg-red-50 text-slate-700 hover:text-red-700"
                              : "bg-emerald-50 hover:bg-emerald-100 text-emerald-700"
                          }`}
                        >
                          {ag.is_active ? "Deactivate" : "Activate"}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-400">
                    No agents registered.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Create Agent Modal */}
      {createOpen && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-md w-full p-6 relative">
            <button onClick={() => setCreateOpen(false)} className="absolute top-5 right-5 text-slate-400 hover:text-slate-700">
              <X className="w-5 h-5" />
            </button>
            <h3 className="text-base font-black text-slate-900 tracking-tight">Create Authorized Agent</h3>
            <p className="text-xs text-slate-500 mt-1">Provide personnel identity details for portal access credentials.</p>

            {createError && (
              <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center space-x-2 text-xs text-red-700">
                <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
                <span>{createError}</span>
              </div>
            )}

            <form onSubmit={handleCreateSubmit} className="mt-5 space-y-4 text-xs">
              <div>
                <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">Full Name *</label>
                <input
                  type="text"
                  required
                  value={createForm.full_name}
                  onChange={(e) => setCreateForm({ ...createForm, full_name: e.target.value })}
                  placeholder="Vikram Sharma"
                  className="mt-1 w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg font-bold text-slate-900 focus:ring-2 focus:ring-red-500 focus:bg-white"
                />
              </div>

              <div>
                <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">Email Address *</label>
                <input
                  type="email"
                  required
                  value={createForm.email}
                  onChange={(e) => setCreateForm({ ...createForm, email: e.target.value })}
                  placeholder="agent@livguard.com"
                  className="mt-1 w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:ring-2 focus:ring-red-500 focus:bg-white"
                />
              </div>

              <div>
                <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">Mobile Number *</label>
                <input
                  type="tel"
                  required
                  value={createForm.mobile}
                  onChange={(e) => setCreateForm({ ...createForm, mobile: e.target.value })}
                  placeholder="9811223344"
                  className="mt-1 w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:ring-2 focus:ring-red-500 focus:bg-white"
                />
              </div>

              <div>
                <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">Initial Password *</label>
                <input
                  type="password"
                  required
                  value={createForm.password}
                  onChange={(e) => setCreateForm({ ...createForm, password: e.target.value })}
                  placeholder="••••••••"
                  className="mt-1 w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:ring-2 focus:ring-red-500 focus:bg-white"
                />
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
                  {createLoading ? "Creating..." : "Create Agent"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Password Reset Modal */}
      {resetOpen && selectedAgent && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-sm w-full p-6 relative">
            <button onClick={() => setResetOpen(false)} className="absolute top-5 right-5 text-slate-400 hover:text-slate-700">
              <X className="w-5 h-5" />
            </button>
            <h3 className="text-base font-black text-slate-900 tracking-tight">Reset Agent Password</h3>
            <p className="text-xs text-slate-500 mt-1">{selectedAgent.full_name} ({selectedAgent.email})</p>

            <form onSubmit={handlePasswordReset} className="mt-5 space-y-4 text-xs">
              <div>
                <label className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">New Password *</label>
                <input
                  type="password"
                  required
                  minLength={6}
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="Minimum 6 characters"
                  className="mt-1 w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:ring-2 focus:ring-red-500 focus:bg-white"
                />
              </div>
              <div className="flex items-center justify-end space-x-3 pt-4 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setResetOpen(false)}
                  className="px-4 py-2 border border-slate-200 rounded-lg text-xs font-semibold text-slate-600 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={resetLoading}
                  className="px-5 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-xs font-bold disabled:opacity-50"
                >
                  {resetLoading ? "Updating..." : "Update Password"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Login History Modal */}
      {historyOpen && selectedAgent && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-lg w-full p-6 relative">
            <button onClick={() => setHistoryOpen(false)} className="absolute top-5 right-5 text-slate-400 hover:text-slate-700">
              <X className="w-5 h-5" />
            </button>
            <h3 className="text-base font-black text-slate-900 tracking-tight">Recent Login History</h3>
            <p className="text-xs text-slate-500 mt-1">{selectedAgent.full_name} ({selectedAgent.email})</p>

            <div className="mt-5 max-h-80 overflow-y-auto space-y-2.5">
              {historyLoading ? (
                <p className="text-xs text-slate-400 text-center py-6">Loading login logs...</p>
              ) : historyLogs.length > 0 ? (
                historyLogs.map((log) => (
                  <div key={log.id} className="p-3 bg-slate-50 border border-slate-200 rounded-xl text-xs flex items-center justify-between">
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className={`px-2 py-0.5 rounded font-bold text-[10px] ${log.status === "SUCCESS" ? "bg-emerald-100 text-emerald-800" : "bg-red-100 text-red-800"}`}>
                          {log.status}
                        </span>
                        <span className="font-mono text-slate-600">IP: {log.ip_address || "Unknown"}</span>
                      </div>
                      <div className="text-[10px] text-slate-400 mt-1 line-clamp-1">{log.user_agent}</div>
                    </div>
                    <span className="text-[10px] text-slate-400 shrink-0 font-medium">{formatDateTime(log.created_at)}</span>
                  </div>
                ))
              ) : (
                <p className="text-xs text-slate-400 text-center py-6">No login attempts recorded yet.</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
