"use client";

import React, { useState, useEffect, useCallback } from "react";
import axios from "axios";
import {
  Activity, ShieldAlert, CheckCircle, RefreshCw,
  ArrowUpRight, Zap, Play, TerminalSquare, BarChart3, Database,
  Shield, Clock, Eye, XCircle, CheckCircle2, AlertTriangle
} from "lucide-react";

const API_BASE = "http://127.0.0.1:8000/api/v1";

export default function RecoveryOSDashboard() {
  const [activeTab, setActiveTab] = useState<"live" | "benchmark" | "reviews" | "audit">("live");
  const [logs, setLogs] = useState<{ id: string; text: string; type: string }[]>([]);
  const [isRecovering, setIsRecovering] = useState(false);

  const [customAmountRupees, setCustomAmountRupees] = useState<number>(150);
  const [customReason, setCustomReason] = useState<string>("insufficient_funds");

  const [isSimulating, setIsSimulating] = useState(false);
  const [benchmarkData, setBenchmarkData] = useState<any>(null);

  const [analytics, setAnalytics] = useState<any>(null);

  const [reviews, setReviews] = useState<any[]>([]);
  const [reviewsLoading, setReviewsLoading] = useState(false);

  const [auditPaymentId, setAuditPaymentId] = useState<string>("");
  const [auditTrail, setAuditTrail] = useState<any>(null);
  const [auditLoading, setAuditLoading] = useState(false);

  const addLog = (text: string, type: "info" | "success" | "warning" | "error") => {
    setLogs((prev) => [{ id: `${Date.now()}-${Math.random()}`, text, type }, ...prev]);
  };

  const fetchAnalytics = useCallback(async () => {
    try {
      const response = await axios.get(`${API_BASE}/analytics/summary`);
      setAnalytics(response.data);
    } catch (err) {

    }
  }, []);

  useEffect(() => {
    fetchAnalytics();
    const interval = setInterval(fetchAnalytics, 10000);
    return () => clearInterval(interval);
  }, [fetchAnalytics]);

  const simulateFailure = async (amountRupees: number, reason: string) => {
    setIsRecovering(true);
    const amountPaise = amountRupees * 100;
    const paymentId = `pay_${Math.random().toString(36).substring(2, 10)}`;

    addLog(`[DETECT] ⚡ Failure Detected: ${paymentId} | ₹${amountRupees.toLocaleString()} | ${reason}`, "warning");

    try {
      addLog(`[AGENT] 🧠 AI Analyst evaluating recovery probability...`, "info");

      const response = await axios.post(`${API_BASE}/recoveries/execute`, {
        payment_id: paymentId,
        customer_id: "cust_demo_888",
        amount: amountPaise,
        failure_reason: reason,
      });

      const data = response.data;

      if (data.status === "escalated") {
        addLog(`[ESCALATE] 🔶 Escalated to human review: ${data.message}`, "warning");
        addLog(`[REVIEW] Review ID: ${data.provider_reference}`, "info");
      } else if (data.status === "failed" && data.message.includes("Policy Blocked")) {
        addLog(`[POLICY] 🛑 Blocked: ${data.message}`, "error");
      } else if (data.status === "failed") {
        addLog(`[STOP] ⏹ Stopping rule triggered: ${data.message}`, "error");
      } else {
        addLog(`[AGENT] ✅ Diagnosis Complete. Action: ${data.action_type}`, "success");
        addLog(`[EXEC] 🔗 Razorpay Order Created: ${data.provider_reference} (${data.execution_id.slice(0, 16)}...)`, "success");
      }

      fetchAnalytics();
    } catch (error: any) {
      addLog(`[ERROR] System Error: ${error.response?.data?.detail || error.message}`, "error");
    } finally {
      setIsRecovering(false);
    }
  };

  const runBenchmarkSimulation = async () => {
    setIsSimulating(true);
    try {
      const response = await axios.post(`${API_BASE}/analytics/simulate-benchmark`);
      setBenchmarkData(response.data);
    } catch (error) {
      console.error("Simulation failed", error);
    } finally {
      setIsSimulating(false);
    }
  };

  const fetchReviews = async () => {
    setReviewsLoading(true);
    try {
      const response = await axios.get(`${API_BASE}/reviews?status=all`);
      setReviews(response.data.reviews || []);
    } catch (error) {
      console.error("Failed to fetch reviews", error);
    } finally {
      setReviewsLoading(false);
    }
  };

  const handleApprove = async (reviewId: string) => {
    try {
      await axios.post(`${API_BASE}/reviews/${reviewId}/approve`);
      addLog(`[REVIEW] ✅ Review ${reviewId.slice(0, 16)}... APPROVED`, "success");
      fetchReviews();
      fetchAnalytics();
    } catch (error) {
      console.error("Approve failed", error);
    }
  };

  const handleReject = async (reviewId: string) => {
    try {
      await axios.post(`${API_BASE}/reviews/${reviewId}/reject`);
      addLog(`[REVIEW] ❌ Review ${reviewId.slice(0, 16)}... REJECTED`, "warning");
      fetchReviews();
    } catch (error) {
      console.error("Reject failed", error);
    }
  };

  const fetchAuditTrail = async () => {
    if (!auditPaymentId.trim()) return;
    setAuditLoading(true);
    try {
      const response = await axios.get(`${API_BASE}/audit/${auditPaymentId}`);
      setAuditTrail(response.data);
    } catch (error: any) {
      setAuditTrail({ error: error.response?.data?.detail || "Not found" });
    } finally {
      setAuditLoading(false);
    }
  };

  const handleCustomSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    simulateFailure(customAmountRupees, customReason);
  };

  const tabs = [
    { key: "live", label: "Live Control Room" },
    { key: "benchmark", label: "50k Benchmark" },
    { key: "reviews", label: "Pending Reviews" },
    { key: "audit", label: "Audit Trail" },
  ];

  return (
    <div className="min-h-screen bg-[#070B14] text-gray-100 p-4 md:p-8 font-sans selection:bg-blue-500/30">
      <div className="max-w-7xl mx-auto space-y-8">

        <header className="flex flex-col md:flex-row md:items-center justify-between border-b border-gray-800 pb-6 gap-4">
          <div className="flex items-center gap-4">
            <div className="bg-gradient-to-br from-blue-600 to-indigo-600 p-3 rounded-xl shadow-lg shadow-blue-900/20">
              <Zap className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-white to-gray-400 bg-clip-text text-transparent">
                RecoveryOS
              </h1>
              <p className="text-blue-400 text-sm font-medium mt-1">Razorpay Track 03: Autonomous Revenue Recovery</p>
            </div>
          </div>
          <div className="flex items-center space-x-2 bg-[#0A1A14] text-green-400 border border-green-500/30 px-4 py-2 rounded-full font-medium text-sm shadow-[0_0_20px_rgba(34,197,94,0.15)]">
            <Database className="w-4 h-4" />
            <span>PostgreSQL + Razorpay Test API Live</span>
          </div>
        </header>

        <div className="flex space-x-6 border-b border-gray-800 pb-px overflow-x-auto">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => {
                setActiveTab(tab.key as any);
                if (tab.key === "reviews") fetchReviews();
              }}
              className={`pb-3 font-semibold text-sm transition-all border-b-2 whitespace-nowrap ${activeTab === tab.key
                  ? "border-blue-500 text-blue-400"
                  : "border-transparent text-gray-500 hover:text-gray-300"
                }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {activeTab === "live" && (
          <div className="animate-in fade-in duration-500 space-y-8">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-5">
              <div className="bg-gradient-to-b from-[#111827] to-[#0B0F19] p-5 rounded-2xl border border-gray-800 shadow-xl relative overflow-hidden">
                <div className="absolute top-0 right-0 w-32 h-32 bg-blue-500/5 rounded-full blur-3xl -mr-10 -mt-10"></div>
                <div className="flex justify-between items-start">
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Total Executions</p>
                  <Activity className="w-4 h-4 text-blue-400" />
                </div>
                <p className="text-3xl font-bold mt-3 text-white">{analytics?.total_executions ?? "—"}</p>
              </div>

              <div className="bg-gradient-to-b from-[#111827] to-[#0B0F19] p-5 rounded-2xl border border-gray-800 shadow-xl relative overflow-hidden">
                <div className="absolute top-0 right-0 w-32 h-32 bg-green-500/5 rounded-full blur-3xl -mr-10 -mt-10"></div>
                <div className="flex justify-between items-start">
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Recovered</p>
                  <CheckCircle className="w-4 h-4 text-green-400" />
                </div>
                <p className="text-3xl font-bold mt-3 text-green-400">{analytics?.successful_recoveries ?? "—"}</p>
              </div>

              <div className="bg-gradient-to-b from-[#111827] to-[#0B0F19] p-5 rounded-2xl border border-gray-800 shadow-xl relative overflow-hidden">
                <div className="absolute top-0 right-0 w-32 h-32 bg-amber-500/5 rounded-full blur-3xl -mr-10 -mt-10"></div>
                <div className="flex justify-between items-start">
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Pending Reviews</p>
                  <ShieldAlert className="w-4 h-4 text-amber-500" />
                </div>
                <p className="text-3xl font-bold mt-3 text-amber-400">{analytics?.pending_reviews ?? "—"}</p>
              </div>

              <div className="bg-gradient-to-b from-[#111827] to-[#0B0F19] p-5 rounded-2xl border border-gray-800 shadow-xl relative overflow-hidden">
                <div className="absolute top-0 right-0 w-32 h-32 bg-emerald-500/5 rounded-full blur-3xl -mr-10 -mt-10"></div>
                <div className="flex justify-between items-start">
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Recovery Rate</p>
                  <ArrowUpRight className="w-4 h-4 text-emerald-400" />
                </div>
                <p className="text-3xl font-bold mt-3 text-emerald-400">{analytics?.recovery_rate_percent ?? "—"}%</p>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
              <div className="lg:col-span-1 space-y-4">
                <h2 className="text-lg font-semibold flex items-center gap-2 text-gray-200">
                  <Play className="w-5 h-5 text-indigo-400" /> Inject Event
                </h2>
                <form onSubmit={handleCustomSubmit} className="bg-[#111827] p-6 rounded-2xl border border-gray-800 space-y-5 shadow-xl">
                  <div>
                    <label className="block text-sm font-medium text-gray-400 mb-2">Amount (₹)</label>
                    <div className="relative">
                      <span className="absolute left-3 top-3.5 text-gray-500 font-medium">₹</span>
                      <input
                        type="number"
                        value={customAmountRupees}
                        onChange={(e) => setCustomAmountRupees(Number(e.target.value))}
                        className="w-full bg-[#0B0F19] border border-gray-700 text-white rounded-xl pl-8 p-3 focus:ring-2 focus:ring-indigo-500 outline-none transition-all"
                        required
                        min="1"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-400 mb-2">Failure Reason</label>
                    <select
                      value={customReason}
                      onChange={(e) => setCustomReason(e.target.value)}
                      className="w-full bg-[#0B0F19] border border-gray-700 text-white rounded-xl p-3 focus:ring-2 focus:ring-indigo-500 outline-none transition-all"
                    >
                      <option value="insufficient_funds">Insufficient Funds</option>
                      <option value="temporary_network_timeout">Network Timeout</option>
                      <option value="suspected_fraud">Suspected Fraud</option>
                      <option value="card_expired">Card Expired</option>
                    </select>
                  </div>

                  <button
                    type="submit"
                    disabled={isRecovering}
                    className="w-full flex justify-center items-center gap-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-bold py-3.5 px-4 rounded-xl transition-all disabled:opacity-50 shadow-lg shadow-blue-900/30 mt-2"
                  >
                    {isRecovering ? <RefreshCw className="w-5 h-5 animate-spin" /> : <Activity className="w-5 h-5" />}
                    {isRecovering ? "Processing..." : "Run AI Recovery"}
                  </button>
                </form>
              </div>

              <div className="lg:col-span-2 space-y-4">
                <h2 className="text-lg font-semibold flex items-center gap-2 text-gray-200">
                  <TerminalSquare className="w-5 h-5 text-indigo-400" /> System Audit Trail
                </h2>
                <div className="bg-[#0A0D14] rounded-2xl border border-gray-800 p-6 h-[420px] overflow-y-auto font-mono text-sm shadow-inner relative">
                  {logs.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-full text-gray-600">
                      <TerminalSquare className="w-10 h-10 mb-3 opacity-20" />
                      <p>System idle. Awaiting revenue risk events...</p>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {logs.map((log) => (
                        <div key={log.id} className={`p-3 rounded-lg border border-l-4 shadow-sm ${log.type === "error" ? "bg-red-950/20 border-red-900/50 border-l-red-500 text-red-300" :
                            log.type === "success" ? "bg-green-950/20 border-green-900/50 border-l-green-500 text-green-300" :
                              log.type === "warning" ? "bg-amber-950/20 border-amber-900/50 border-l-amber-500 text-amber-300" :
                                "bg-blue-950/20 border-blue-900/50 border-l-blue-500 text-blue-300"
                          }`}>
                          <span className="text-gray-500 mr-3 text-xs">[{new Date(parseInt(log.id.split("-")[0])).toLocaleTimeString()}]</span>
                          {log.text}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === "benchmark" && (
          <div className="animate-in fade-in duration-500 bg-gradient-to-b from-[#111827] to-[#0B0F19] p-8 rounded-3xl border border-gray-800 shadow-2xl">
            <div className="flex items-center justify-between mb-8">
              <div className="flex items-center gap-3">
                <BarChart3 className="w-8 h-8 text-blue-500" />
                <h2 className="text-2xl font-bold text-white tracking-tight">50,000 Event Evaluation Harness</h2>
              </div>
              <button
                onClick={runBenchmarkSimulation}
                disabled={isSimulating}
                className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white px-6 py-2.5 rounded-lg font-medium transition disabled:opacity-50"
              >
                {isSimulating ? <RefreshCw className="w-5 h-5 animate-spin" /> : <Play className="w-5 h-5" />}
                {isSimulating ? "Running..." : "Run Simulation"}
              </button>
            </div>

            {!benchmarkData && !isSimulating && (
              <div className="py-20 text-center text-gray-500">
                <Database className="w-12 h-12 mx-auto mb-4 opacity-20" />
                <p>Click &ldquo;Run Simulation&rdquo; to generate and evaluate 50,000 synthetic events via the API.</p>
              </div>
            )}

            {isSimulating && (
              <div className="py-20 text-center text-blue-400">
                <RefreshCw className="w-12 h-12 mx-auto mb-4 animate-spin opacity-50" />
                <p className="animate-pulse">Synthesizing events and running through Policy Engine...</p>
              </div>
            )}

            {benchmarkData && !isSimulating && (
              <div className="animate-in fade-in duration-500">
                <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
                  <div className="bg-[#0B0F19] p-5 rounded-2xl border border-gray-800 shadow-inner">
                    <p className="text-xs font-semibold text-gray-500 mb-2 uppercase tracking-wider">Baseline Recovery</p>
                    <p className="text-xl font-mono text-gray-300">₹{(benchmarkData.baseline_recovery_paise / 100).toLocaleString()}</p>
                  </div>
                  <div className="bg-[#0B0F19] p-5 rounded-2xl border border-gray-800 shadow-inner">
                    <p className="text-xs font-semibold text-gray-500 mb-2 uppercase tracking-wider">Agent Recovery</p>
                    <p className="text-xl font-mono text-green-400">₹{(benchmarkData.ai_recovery_paise / 100).toLocaleString()}</p>
                  </div>
                  <div className="bg-[#0B0F19] p-5 rounded-2xl border border-gray-800 shadow-inner">
                    <p className="text-xs font-semibold text-gray-500 mb-2 uppercase tracking-wider">Uplift</p>
                    <p className="text-xl font-mono text-blue-400">+{benchmarkData.incremental_uplift_percent}%</p>
                  </div>
                  <div className="bg-[#0B0F19] p-5 rounded-2xl border border-gray-800 shadow-inner">
                    <p className="text-xs font-semibold text-gray-500 mb-2 uppercase tracking-wider">Policy Blocks</p>
                    <p className="text-xl font-mono text-amber-400">{benchmarkData.policy_blocks.toLocaleString()}</p>
                  </div>
                  <div className="bg-[#0B0F19] p-5 rounded-2xl border border-gray-800 shadow-inner relative overflow-hidden">
                    <div className="absolute top-0 right-0 w-16 h-16 bg-green-500/10 rounded-full blur-xl -mr-4 -mt-4"></div>
                    <p className="text-xs font-semibold text-gray-500 mb-2 uppercase tracking-wider">Unsafe Actions</p>
                    <p className="text-xl font-mono text-green-400">{benchmarkData.unsafe_action_rate}%</p>
                  </div>
                </div>

                <div className="bg-[#05080F] p-6 rounded-2xl border border-gray-800 font-mono text-sm text-gray-300 overflow-x-auto whitespace-pre shadow-inner">
                  {`==================== RECOVERY OS EVALUATION RESULTS ====================
Total Synthetic Events Evaluated: ${benchmarkData.total_events.toLocaleString()}

[INTERVENTION SAFETY]
Unsafe action rate:        ${benchmarkData.unsafe_action_rate}%  (Enforced by PolicyEngine)
Policy Engine Blocks:      ${benchmarkData.policy_blocks.toLocaleString()} (High-value, Suspicious, or Stopping Rules)
Escalations to Review:     ${benchmarkData.escalations?.toLocaleString() ?? 'N/A'}

[OUTCOMES]
Baseline recovery (Rules): ₹${(benchmarkData.baseline_recovery_paise / 100).toLocaleString()}
Agent recovery (RecoveryOS): ₹${(benchmarkData.ai_recovery_paise / 100).toLocaleString()}
Recovery uplift:           +${benchmarkData.incremental_uplift_percent}%

CONCLUSION: The AI agent identifies high-probability recovery opportunities
that static rules miss, while strict policy guardrails and stopping rules
guarantee 0% unsafe API execution.`}
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === "reviews" && (
          <div className="animate-in fade-in duration-500 space-y-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Shield className="w-7 h-7 text-amber-500" />
                <h2 className="text-2xl font-bold text-white tracking-tight">Escalation Queue</h2>
              </div>
              <button
                onClick={fetchReviews}
                disabled={reviewsLoading}
                className="flex items-center gap-2 bg-gray-800 hover:bg-gray-700 text-white px-4 py-2 rounded-lg font-medium transition text-sm disabled:opacity-50"
              >
                <RefreshCw className={`w-4 h-4 ${reviewsLoading ? "animate-spin" : ""}`} />
                Refresh
              </button>
            </div>

            {reviews.length === 0 ? (
              <div className="bg-[#111827] rounded-2xl border border-gray-800 p-16 text-center text-gray-500">
                <Shield className="w-12 h-12 mx-auto mb-4 opacity-20" />
                <p className="text-lg">No reviews in queue</p>
                <p className="text-sm mt-2">High-value or suspicious transactions will appear here for manual review.</p>
              </div>
            ) : (
              <div className="space-y-4">
                {reviews.map((review) => (
                  <div key={review.review_id} className="bg-[#111827] rounded-2xl border border-gray-800 p-6 shadow-xl">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 space-y-3">
                        <div className="flex items-center gap-3">
                          <span className={`px-2.5 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${review.status === "pending" ? "bg-amber-900/30 text-amber-400 border border-amber-800" :
                              review.status === "approved" ? "bg-green-900/30 text-green-400 border border-green-800" :
                                "bg-red-900/30 text-red-400 border border-red-800"
                            }`}>
                            {review.status}
                          </span>
                          <span className="text-gray-500 text-sm font-mono">{review.review_id.slice(0, 20)}...</span>
                        </div>

                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                          <div>
                            <span className="text-gray-500 block">Payment</span>
                            <span className="text-white font-mono">{review.payment_id}</span>
                          </div>
                          <div>
                            <span className="text-gray-500 block">Amount</span>
                            <span className="text-white font-bold">₹{(review.amount / 100).toLocaleString()}</span>
                          </div>
                          <div>
                            <span className="text-gray-500 block">Action</span>
                            <span className="text-blue-400">{review.action_type}</span>
                          </div>
                          <div>
                            <span className="text-gray-500 block">AI Confidence</span>
                            <span className="text-white">{(review.ai_confidence * 100).toFixed(0)}%</span>
                          </div>
                        </div>

                        <div className="text-sm">
                          <span className="text-gray-500">Policy Reason: </span>
                          <span className="text-amber-300">{review.policy_reason}</span>
                        </div>
                        {review.ai_diagnosis && (
                          <div className="text-sm">
                            <span className="text-gray-500">AI Diagnosis: </span>
                            <span className="text-gray-300">{review.ai_diagnosis.slice(0, 200)}{review.ai_diagnosis.length > 200 ? "..." : ""}</span>
                          </div>
                        )}
                      </div>

                      {review.status === "pending" && (
                        <div className="flex flex-col gap-2">
                          <button
                            onClick={() => handleApprove(review.review_id)}
                            className="flex items-center gap-1.5 bg-green-600 hover:bg-green-500 text-white px-4 py-2 rounded-lg font-medium text-sm transition shadow-lg shadow-green-900/20"
                          >
                            <CheckCircle2 className="w-4 h-4" />
                            Approve
                          </button>
                          <button
                            onClick={() => handleReject(review.review_id)}
                            className="flex items-center gap-1.5 bg-red-600/80 hover:bg-red-500 text-white px-4 py-2 rounded-lg font-medium text-sm transition"
                          >
                            <XCircle className="w-4 h-4" />
                            Reject
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === "audit" && (
          <div className="animate-in fade-in duration-500 space-y-6">
            <div className="flex items-center gap-3">
              <Eye className="w-7 h-7 text-indigo-500" />
              <h2 className="text-2xl font-bold text-white tracking-tight">Payment Audit Trail</h2>
            </div>

            <div className="flex gap-3">
              <input
                type="text"
                value={auditPaymentId}
                onChange={(e) => setAuditPaymentId(e.target.value)}
                placeholder="Enter payment ID (e.g. pay_abc123)"
                className="flex-1 bg-[#0B0F19] border border-gray-700 text-white rounded-xl p-3 focus:ring-2 focus:ring-indigo-500 outline-none transition-all font-mono"
              />
              <button
                onClick={fetchAuditTrail}
                disabled={auditLoading || !auditPaymentId.trim()}
                className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-6 py-3 rounded-xl font-medium transition disabled:opacity-50"
              >
                {auditLoading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Eye className="w-4 h-4" />}
                Lookup
              </button>
            </div>

            {auditTrail?.error && (
              <div className="bg-red-950/20 border border-red-900/50 text-red-300 p-4 rounded-xl">
                {auditTrail.error}
              </div>
            )}

            {auditTrail?.trail && (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <p className="text-gray-400 text-sm">{auditTrail.total_entries} events for <span className="text-white font-mono">{auditTrail.payment_id}</span></p>
                </div>

                <div className="relative">
                  <div className="absolute left-[19px] top-0 bottom-0 w-0.5 bg-gray-800"></div>

                  <div className="space-y-4">
                    {auditTrail.trail.map((entry: any, i: number) => {
                      const iconMap: Record<string, { icon: any; color: string }> = {
                        failure_detected: { icon: AlertTriangle, color: "text-amber-500" },
                        ai_diagnosis: { icon: Activity, color: "text-blue-400" },
                        policy_decision: { icon: Shield, color: "text-indigo-400" },
                        execution_started: { icon: Play, color: "text-cyan-400" },
                        execution_succeeded: { icon: CheckCircle, color: "text-green-400" },
                        execution_failed: { icon: XCircle, color: "text-red-400" },
                        escalated_to_review: { icon: ShieldAlert, color: "text-amber-400" },
                        review_approved: { icon: CheckCircle2, color: "text-green-400" },
                        review_rejected: { icon: XCircle, color: "text-red-400" },
                        stopping_rule_triggered: { icon: Clock, color: "text-red-400" },
                      };

                      const config = iconMap[entry.event_type] || { icon: Activity, color: "text-gray-400" };
                      const Icon = config.icon;

                      return (
                        <div key={i} className="relative flex gap-4 pl-2">
                          <div className={`relative z-10 flex-shrink-0 w-9 h-9 rounded-full bg-[#111827] border border-gray-700 flex items-center justify-center`}>
                            <Icon className={`w-4 h-4 ${config.color}`} />
                          </div>
                          <div className="flex-1 bg-[#111827] rounded-xl border border-gray-800 p-4 shadow-lg">
                            <div className="flex items-center justify-between mb-2">
                              <span className={`text-sm font-semibold ${config.color}`}>
                                {entry.event_type.replace(/_/g, " ").toUpperCase()}
                              </span>
                              <span className="text-xs text-gray-500">
                                {entry.created_at ? new Date(entry.created_at).toLocaleString() : ""}
                              </span>
                            </div>
                            <div className="text-xs text-gray-400 font-mono bg-[#0B0F19] p-3 rounded-lg overflow-x-auto">
                              {JSON.stringify(entry.data, null, 2)}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            )}

            {!auditTrail && (
              <div className="bg-[#111827] rounded-2xl border border-gray-800 p-16 text-center text-gray-500">
                <Eye className="w-12 h-12 mx-auto mb-4 opacity-20" />
                <p className="text-lg">Enter a payment ID to view its complete audit trail</p>
                <p className="text-sm mt-2">Every step of the recovery pipeline is recorded: detection → AI diagnosis → policy → execution → reconciliation</p>
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  );
}
