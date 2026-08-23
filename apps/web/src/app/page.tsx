"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import axios from "axios";
import { motion, AnimatePresence } from "framer-motion";
import {
  Activity, ShieldAlert, CheckCircle, RefreshCw, ArrowUpRight,
  Zap, Play, BarChart3, Database, Shield, Clock, Eye, XCircle,
  CheckCircle2, AlertTriangle, ChevronDown, ChevronRight,
  ArrowRight, CreditCard, TrendingUp, Search
} from "lucide-react";

const API_BASE = "http://127.0.0.1:8000/api/v1";

type PipelineStage = "idle" | "detect" | "diagnose" | "policy" | "execute" | "result";
type PipelineResult = "success" | "escalated" | "blocked" | "error" | null;

interface Transaction {
  execution_id: string;
  payment_id: string;
  action_type: string;
  status: string;
  message: string;
  external_reference: string | null;
  created_at: string | null;
}

const STAGES = [
  { key: "detect", label: "Detect", icon: AlertTriangle, desc: "Payment failure detected" },
  { key: "diagnose", label: "AI Diagnose", icon: Activity, desc: "Gemini 2.5 Flash analyzing" },
  { key: "policy", label: "Policy Gate", icon: Shield, desc: "Safety boundary check" },
  { key: "execute", label: "Execute", icon: Play, desc: "Razorpay API call" },
  { key: "result", label: "Result", icon: CheckCircle, desc: "Recovery outcome" },
] as const;

export default function RecoveryOSDashboard() {
  const [activeTab, setActiveTab] = useState<"live" | "benchmark" | "reviews" | "audit">("live");

  const [pipelineStage, setPipelineStage] = useState<PipelineStage>("idle");
  const [pipelineResult, setPipelineResult] = useState<PipelineResult>(null);
  const [pipelineData, setPipelineData] = useState<Record<string, any>>({});
  const [isRecovering, setIsRecovering] = useState(false);

  const [customAmountRupees, setCustomAmountRupees] = useState<number>(150);
  const [customReason, setCustomReason] = useState<string>("insufficient_funds");

  const [isSimulating, setIsSimulating] = useState(false);
  const [benchmarkData, setBenchmarkData] = useState<any>(null);

  const [analytics, setAnalytics] = useState<any>(null);
  const [recentTxns, setRecentTxns] = useState<Transaction[]>([]);
  const [expandedTxn, setExpandedTxn] = useState<string | null>(null);
  const [txnAudit, setTxnAudit] = useState<Record<string, any>>({});

  const [reviews, setReviews] = useState<any[]>([]);
  const [reviewsLoading, setReviewsLoading] = useState(false);

  const [auditPaymentId, setAuditPaymentId] = useState<string>("");
  const [auditTrail, setAuditTrail] = useState<any>(null);
  const [auditLoading, setAuditLoading] = useState(false);

  const fetchAnalytics = useCallback(async () => {
    try {
      const response = await axios.get(`${API_BASE}/analytics/summary`);
      setAnalytics(response.data);
      if (response.data.recent_transactions) {
        setRecentTxns(response.data.recent_transactions);
      }
    } catch (err) { }
  }, []);

  useEffect(() => {
    fetchAnalytics();
    const interval = setInterval(fetchAnalytics, 8000);
    return () => clearInterval(interval);
  }, [fetchAnalytics]);

  const delay = (ms: number) => new Promise(r => setTimeout(r, ms));

  const simulateFailure = async (amountRupees: number, reason: string) => {
    setIsRecovering(true);
    setPipelineResult(null);
    setPipelineData({});

    const amountPaise = amountRupees * 100;
    const paymentId = `pay_${Math.random().toString(36).substring(2, 10)}`;

    setPipelineStage("detect");
    setPipelineData({ payment_id: paymentId, amount: `₹${amountRupees.toLocaleString()}`, reason });
    await delay(600);

    setPipelineStage("diagnose");
    setPipelineData(prev => ({ ...prev, stage_info: "AI agent evaluating recovery probability..." }));

    try {
      const response = await axios.post(`${API_BASE}/recoveries/execute`, {
        payment_id: paymentId,
        customer_id: `cust_demo_${Math.random().toString(36).substring(2, 6)}`,
        amount: amountPaise,
        failure_reason: reason,
      });
      const data = response.data;

      setPipelineStage("policy");
      setPipelineData(prev => ({ ...prev, action: data.action_type, stage_info: "Checking safety rules..." }));
      await delay(500);

      if (data.status === "escalated") {
        setPipelineStage("result");
        setPipelineResult("escalated");
        setPipelineData(prev => ({
          ...prev,
          result_status: "ESCALATED",
          message: data.message,
          review_id: data.provider_reference,
          stage_info: "Requires human approval",
        }));
      } else if (data.status === "failed") {
        setPipelineStage("result");
        setPipelineResult("blocked");
        setPipelineData(prev => ({
          ...prev,
          result_status: "BLOCKED",
          message: data.message,
          stage_info: "Policy engine denied",
        }));
      } else {
        setPipelineStage("execute");
        setPipelineData(prev => ({ ...prev, stage_info: "Creating Razorpay retry order..." }));
        await delay(400);

        setPipelineStage("result");
        setPipelineResult("success");
        setPipelineData(prev => ({
          ...prev,
          result_status: "RECOVERED",
          execution_id: data.execution_id,
          provider_ref: data.provider_reference,
          message: data.message,
          stage_info: "Recovery order created",
        }));
      }

      fetchAnalytics();
    } catch (error: any) {
      setPipelineStage("result");
      setPipelineResult("error");
      setPipelineData(prev => ({
        ...prev,
        result_status: "ERROR",
        message: error.response?.data?.detail || error.message,
        stage_info: "System error",
      }));
    } finally {
      setIsRecovering(false);
    }
  };

  const handleCustomSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    simulateFailure(customAmountRupees, customReason);
  };

  const toggleTxnAudit = async (paymentId: string) => {
    if (expandedTxn === paymentId) {
      setExpandedTxn(null);
      return;
    }
    setExpandedTxn(paymentId);
    if (!txnAudit[paymentId]) {
      try {
        const response = await axios.get(`${API_BASE}/audit/${paymentId}`);
        setTxnAudit(prev => ({ ...prev, [paymentId]: response.data }));
      } catch {
        setTxnAudit(prev => ({ ...prev, [paymentId]: { error: "No audit trail found" } }));
      }
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
      fetchReviews();
      fetchAnalytics();
    } catch (error) {
      console.error("Approve failed", error);
    }
  };

  const handleReject = async (reviewId: string) => {
    try {
      await axios.post(`${API_BASE}/reviews/${reviewId}/reject`);
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

  const getStageState = (stageKey: string) => {
    const stageOrder = ["detect", "diagnose", "policy", "execute", "result"];
    const currentIdx = stageOrder.indexOf(pipelineStage);
    const thisIdx = stageOrder.indexOf(stageKey);

    if (pipelineStage === "idle") return "idle";
    if (thisIdx < currentIdx) return "complete";
    if (thisIdx === currentIdx) return "active";
    return "pending";
  };

  const stageColors: Record<string, string> = {
    idle: "border-gray-700 bg-gray-900/50 text-gray-600",
    pending: "border-gray-700 bg-gray-900/50 text-gray-600",
    active: "border-blue-500 bg-blue-950/40 text-blue-400 shadow-[0_0_30px_rgba(59,130,246,0.25)]",
    complete: "border-green-600/60 bg-green-950/30 text-green-400",
  };

  const resultColors: Record<string, string> = {
    success: "border-green-500 bg-green-950/40 text-green-400 shadow-[0_0_30px_rgba(34,197,94,0.25)]",
    escalated: "border-amber-500 bg-amber-950/40 text-amber-400 shadow-[0_0_30px_rgba(245,158,11,0.25)]",
    blocked: "border-red-500 bg-red-950/40 text-red-400 shadow-[0_0_30px_rgba(239,68,68,0.25)]",
    error: "border-red-500 bg-red-950/40 text-red-400 shadow-[0_0_30px_rgba(239,68,68,0.25)]",
  };

  const tabs = [
    { key: "live", label: "Live Recovery", icon: Zap },
    { key: "benchmark", label: "50k Benchmark", icon: BarChart3 },
    { key: "reviews", label: "Escalation Queue", icon: Shield },
    { key: "audit", label: "Audit Trail", icon: Eye },
  ];

  return (
    <div className="min-h-screen bg-[#060910] text-gray-100 font-sans selection:bg-blue-500/30">
      <div className="max-w-[1400px] mx-auto px-4 md:px-8 py-6 space-y-6">

        {/* Header */}
        <header className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="relative">
              <div className="bg-gradient-to-br from-blue-600 to-indigo-600 p-3 rounded-2xl shadow-lg shadow-blue-900/30">
                <Zap className="w-7 h-7 text-white" />
              </div>
              <div className="absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full border-2 border-[#060910] animate-pulse" />
            </div>
            <div>
              <h1 className="text-3xl font-black tracking-tight bg-gradient-to-r from-white via-white to-gray-400 bg-clip-text text-transparent">
                RecoveryOS
              </h1>
              <p className="text-blue-400/80 text-sm font-medium">Razorpay AI Buildathon · Track 03</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 bg-green-500/10 text-green-400 border border-green-500/20 px-3 py-1.5 rounded-lg text-xs font-medium">
              <div className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse" />
              PostgreSQL Live
            </div>
            <div className="flex items-center gap-2 bg-blue-500/10 text-blue-400 border border-blue-500/20 px-3 py-1.5 rounded-lg text-xs font-medium">
              <CreditCard className="w-3 h-3" />
              Razorpay Test Mode
            </div>
          </div>
        </header>

        {/* Navigation */}
        <nav className="flex gap-1 bg-[#0A0E18] p-1 rounded-xl border border-gray-800/50">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.key}
                onClick={() => {
                  setActiveTab(tab.key as any);
                  if (tab.key === "reviews") fetchReviews();
                }}
                className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${activeTab === tab.key
                  ? "bg-[#141B2D] text-white shadow-sm border border-gray-700/50"
                  : "text-gray-500 hover:text-gray-300"
                  }`}
              >
                <Icon className="w-4 h-4" />
                {tab.label}
              </button>
            );
          })}
        </nav>

        {/* ============ LIVE TAB ============ */}
        {activeTab === "live" && (
          <div className="space-y-6">
            {/* Metrics */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
              {[
                { label: "Total Runs", value: analytics?.total_executions ?? "—", icon: Activity, color: "blue" },
                { label: "Recovered", value: analytics?.successful_recoveries ?? "—", icon: CheckCircle, color: "green" },
                { label: "Blocked", value: analytics?.failed_recoveries ?? "—", icon: XCircle, color: "red" },
                { label: "Pending Review", value: analytics?.pending_reviews ?? "—", icon: ShieldAlert, color: "amber" },
                { label: "Recovery Rate", value: `${analytics?.recovery_rate_percent ?? "—"}%`, icon: TrendingUp, color: "emerald" },
              ].map((metric) => {
                const Icon = metric.icon;
                return (
                  <motion.div
                    key={metric.label}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className={`bg-[#0C1120] p-4 rounded-xl border border-gray-800/60 relative overflow-hidden`}
                  >
                    <div className={`absolute top-0 right-0 w-20 h-20 bg-${metric.color}-500/5 rounded-full blur-2xl -mr-6 -mt-6`} />
                    <div className="flex items-center gap-2 mb-2">
                      <Icon className={`w-3.5 h-3.5 text-${metric.color}-400`} />
                      <span className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider">{metric.label}</span>
                    </div>
                    <p className="text-2xl font-bold text-white">{metric.value}</p>
                  </motion.div>
                );
              })}
            </div>

            {/* Pipeline Visualization */}
            <div className="bg-[#0A0E18] rounded-2xl border border-gray-800/60 p-6 overflow-hidden">
              <div className="flex items-center gap-2 mb-6">
                <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
                <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">Recovery Pipeline</h2>
              </div>

              {/* Pipeline Stages */}
              <div className="flex items-stretch gap-0 overflow-x-auto pb-2">
                {STAGES.map((stage, i) => {
                  const Icon = stage.icon;
                  const state = getStageState(stage.key);
                  const isResultStage = stage.key === "result" && pipelineResult;
                  const colorClass = isResultStage && state === "active"
                    ? resultColors[pipelineResult!]
                    : stageColors[state];

                  return (
                    <React.Fragment key={stage.key}>
                      {i > 0 && (
                        <div className="flex items-center px-1 flex-shrink-0">
                          <motion.div
                            initial={false}
                            animate={{
                              backgroundColor: state === "complete" || state === "active" ? "#22c55e" : "#1f2937",
                              scaleX: state === "complete" ? 1 : state === "active" ? 0.6 : 0.3,
                            }}
                            className="w-8 h-0.5 rounded-full origin-left"
                            transition={{ duration: 0.3 }}
                          />
                          <ArrowRight className={`w-3 h-3 flex-shrink-0 ${state === "complete" || state === "active" ? "text-green-500" : "text-gray-700"}`} />
                        </div>
                      )}
                      <motion.div
                        layout
                        initial={false}
                        animate={{
                          scale: state === "active" ? 1.02 : 1,
                        }}
                        transition={{ type: "spring", stiffness: 300, damping: 25 }}
                        className={`flex-1 min-w-[140px] p-4 rounded-xl border-2 transition-colors duration-500 ${colorClass}`}
                      >
                        <div className="flex items-center gap-2 mb-2">
                          {state === "active" && !isResultStage && (
                            <motion.div
                              animate={{ rotate: 360 }}
                              transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }}
                            >
                              <RefreshCw className="w-4 h-4" />
                            </motion.div>
                          )}
                          {state === "complete" && <CheckCircle className="w-4 h-4 text-green-400" />}
                          {(state === "idle" || state === "pending") && <Icon className="w-4 h-4" />}
                          {state === "active" && isResultStage && (
                            pipelineResult === "success" ? <CheckCircle className="w-4 h-4" /> :
                              pipelineResult === "escalated" ? <ShieldAlert className="w-4 h-4" /> :
                                <XCircle className="w-4 h-4" />
                          )}
                          <span className="text-xs font-bold uppercase tracking-wider">{stage.label}</span>
                        </div>
                        <p className="text-[11px] opacity-70">
                          {state === "active" ? (pipelineData.stage_info || stage.desc) : stage.desc}
                        </p>
                        {state === "active" && pipelineData.result_status && stage.key === "result" && (
                          <motion.div
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: "auto" }}
                            className="mt-2 pt-2 border-t border-current/20"
                          >
                            <p className="text-xs font-bold">{pipelineData.result_status}</p>
                            {pipelineData.provider_ref && (
                              <p className="text-[10px] opacity-70 font-mono mt-0.5">Ref: {pipelineData.provider_ref}</p>
                            )}
                          </motion.div>
                        )}
                      </motion.div>
                    </React.Fragment>
                  );
                })}
              </div>

              {/* Quick Action Panel */}
              <div className="mt-6 pt-5 border-t border-gray-800/60">
                <form onSubmit={handleCustomSubmit} className="flex items-end gap-3 flex-wrap">
                  <div className="flex-1 min-w-[140px]">
                    <label className="block text-[11px] font-semibold text-gray-500 uppercase tracking-wider mb-1.5">Amount</label>
                    <div className="relative">
                      <span className="absolute left-3 top-2.5 text-gray-500 text-sm font-medium">₹</span>
                      <input
                        type="number"
                        value={customAmountRupees}
                        onChange={(e) => setCustomAmountRupees(Number(e.target.value))}
                        className="w-full bg-[#0C1120] border border-gray-700/50 text-white rounded-lg pl-7 pr-3 py-2.5 text-sm focus:ring-1 focus:ring-blue-500/50 outline-none"
                        required
                        min="1"
                      />
                    </div>
                  </div>
                  <div className="flex-1 min-w-[180px]">
                    <label className="block text-[11px] font-semibold text-gray-500 uppercase tracking-wider mb-1.5">Failure Reason</label>
                    <select
                      value={customReason}
                      onChange={(e) => setCustomReason(e.target.value)}
                      className="w-full bg-[#0C1120] border border-gray-700/50 text-white rounded-lg px-3 py-2.5 text-sm focus:ring-1 focus:ring-blue-500/50 outline-none"
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
                    className="flex items-center gap-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-semibold py-2.5 px-6 rounded-lg transition-all disabled:opacity-40 shadow-lg shadow-blue-900/30 text-sm"
                  >
                    {isRecovering ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
                    {isRecovering ? "Recovering..." : "Trigger Recovery"}
                  </button>
                  {pipelineStage !== "idle" && !isRecovering && (
                    <button
                      type="button"
                      onClick={() => { setPipelineStage("idle"); setPipelineResult(null); setPipelineData({}); }}
                      className="text-gray-500 hover:text-gray-300 text-xs underline py-2.5"
                    >
                      Reset
                    </button>
                  )}
                </form>
              </div>
            </div>

            {/* Recent Transactions Table */}
            <div className="bg-[#0A0E18] rounded-2xl border border-gray-800/60 overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-800/60 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Clock className="w-4 h-4 text-gray-500" />
                  <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">Recent Transactions</h2>
                </div>
                <span className="text-xs text-gray-600">{recentTxns.length} records</span>
              </div>

              {recentTxns.length === 0 ? (
                <div className="py-16 text-center text-gray-600">
                  <Database className="w-10 h-10 mx-auto mb-3 opacity-20" />
                  <p className="text-sm">No transactions yet. Trigger a recovery above to see it here.</p>
                </div>
              ) : (
                <div className="divide-y divide-gray-800/40">
                  {recentTxns.map((txn) => {
                    const isExpanded = expandedTxn === txn.payment_id;
                    const statusColors: Record<string, string> = {
                      STARTED: "bg-green-500/10 text-green-400 border-green-500/20",
                      SUCCEEDED: "bg-green-500/10 text-green-400 border-green-500/20",
                      FAILED: "bg-red-500/10 text-red-400 border-red-500/20",
                    };
                    const statusColor = statusColors[txn.status] || "bg-gray-500/10 text-gray-400 border-gray-500/20";

                    return (
                      <div key={txn.execution_id}>
                        <button
                          onClick={() => toggleTxnAudit(txn.payment_id)}
                          className="w-full px-6 py-3.5 flex items-center gap-4 hover:bg-[#0E1326] transition-colors text-left"
                        >
                          <div className="w-5 flex-shrink-0">
                            {isExpanded ? (
                              <ChevronDown className="w-4 h-4 text-gray-500" />
                            ) : (
                              <ChevronRight className="w-4 h-4 text-gray-500" />
                            )}
                          </div>
                          <span className="text-xs font-mono text-gray-400 w-28 flex-shrink-0">{txn.payment_id}</span>
                          <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded border ${statusColor} flex-shrink-0`}>
                            {txn.status}
                          </span>
                          <span className="text-xs text-gray-500 flex-1 truncate">{txn.message}</span>
                          <span className="text-[10px] text-gray-600 flex-shrink-0">
                            {txn.created_at ? new Date(txn.created_at).toLocaleTimeString() : ""}
                          </span>
                        </button>

                        <AnimatePresence>
                          {isExpanded && (
                            <motion.div
                              initial={{ height: 0, opacity: 0 }}
                              animate={{ height: "auto", opacity: 1 }}
                              exit={{ height: 0, opacity: 0 }}
                              transition={{ duration: 0.2 }}
                              className="overflow-hidden"
                            >
                              <div className="px-6 pb-4 pl-16">
                                {txnAudit[txn.payment_id]?.error ? (
                                  <p className="text-xs text-gray-500 italic">{txnAudit[txn.payment_id].error}</p>
                                ) : txnAudit[txn.payment_id]?.trail ? (
                                  <div className="relative pl-4 border-l border-gray-800">
                                    {txnAudit[txn.payment_id].trail.map((entry: any, i: number) => {
                                      const eventColors: Record<string, string> = {
                                        failure_detected: "text-amber-400",
                                        ai_diagnosis: "text-blue-400",
                                        policy_decision: "text-indigo-400",
                                        execution_succeeded: "text-green-400",
                                        execution_failed: "text-red-400",
                                        escalated_to_review: "text-amber-400",
                                        review_approved: "text-green-400",
                                        review_rejected: "text-red-400",
                                        stopping_rule_triggered: "text-red-400",
                                      };
                                      return (
                                        <div key={i} className="relative pb-3 last:pb-0">
                                          <div className="absolute -left-[19px] top-1 w-2.5 h-2.5 rounded-full bg-[#0A0E18] border-2 border-gray-600" />
                                          <div className="flex items-baseline gap-2">
                                            <span className={`text-[11px] font-semibold ${eventColors[entry.event_type] || "text-gray-400"}`}>
                                              {entry.event_type.replace(/_/g, " ")}
                                            </span>
                                            <span className="text-[10px] text-gray-600">
                                              {entry.created_at ? new Date(entry.created_at).toLocaleTimeString() : ""}
                                            </span>
                                          </div>
                                          <pre className="text-[10px] text-gray-500 mt-0.5 font-mono whitespace-pre-wrap break-all">
                                            {JSON.stringify(entry.data, null, 1)}
                                          </pre>
                                        </div>
                                      );
                                    })}
                                  </div>
                                ) : (
                                  <div className="flex items-center gap-2 text-xs text-gray-500">
                                    <RefreshCw className="w-3 h-3 animate-spin" />
                                    Loading audit trail...
                                  </div>
                                )}
                              </div>
                            </motion.div>
                          )}
                        </AnimatePresence>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        )}

        {/* ============ BENCHMARK TAB ============ */}
        {activeTab === "benchmark" && (
          <div className="bg-[#0A0E18] p-8 rounded-2xl border border-gray-800/60">
            <div className="flex items-center justify-between mb-8">
              <div className="flex items-center gap-3">
                <BarChart3 className="w-7 h-7 text-blue-500" />
                <div>
                  <h2 className="text-xl font-bold text-white">50,000 Event Evaluation</h2>
                  <p className="text-xs text-gray-500 mt-0.5">Synthetic batch processed through Policy Engine</p>
                </div>
              </div>
              <button
                onClick={runBenchmarkSimulation}
                disabled={isSimulating}
                className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white px-5 py-2 rounded-lg font-medium text-sm transition disabled:opacity-50"
              >
                {isSimulating ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                {isSimulating ? "Running..." : "Run Simulation"}
              </button>
            </div>

            {!benchmarkData && !isSimulating && (
              <div className="py-20 text-center text-gray-600">
                <Database className="w-10 h-10 mx-auto mb-3 opacity-20" />
                <p className="text-sm">Run simulation to evaluate against 50k synthetic payment failures</p>
              </div>
            )}

            {isSimulating && (
              <div className="py-20 text-center text-blue-400">
                <RefreshCw className="w-10 h-10 mx-auto mb-3 animate-spin opacity-50" />
                <p className="animate-pulse text-sm">Processing events through Policy Engine...</p>
              </div>
            )}

            {benchmarkData && !isSimulating && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
                  {[
                    { label: "Baseline", value: `₹${(benchmarkData.baseline_recovery_paise / 100).toLocaleString()}`, color: "gray" },
                    { label: "AI Recovery", value: `₹${(benchmarkData.ai_recovery_paise / 100).toLocaleString()}`, color: "green" },
                    { label: "Uplift", value: `+${benchmarkData.incremental_uplift_percent}%`, color: "blue" },
                    { label: "Policy Blocks", value: benchmarkData.policy_blocks.toLocaleString(), color: "amber" },
                    { label: "Unsafe Rate", value: `${benchmarkData.unsafe_action_rate}%`, color: "green" },
                  ].map(m => (
                    <div key={m.label} className="bg-[#060910] p-4 rounded-xl border border-gray-800/40">
                      <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-1">{m.label}</p>
                      <p className={`text-lg font-mono font-bold text-${m.color}-400`}>{m.value}</p>
                    </div>
                  ))}
                </div>

                <div className="bg-[#040710] p-5 rounded-xl border border-gray-800/40 font-mono text-xs text-gray-400 overflow-x-auto whitespace-pre leading-relaxed">
{`═══ RECOVERYOS EVALUATION ═══════════════════════════════════
Events: ${benchmarkData.total_events.toLocaleString()}  |  Unsafe: ${benchmarkData.unsafe_action_rate}%  |  Blocks: ${benchmarkData.policy_blocks.toLocaleString()}

Baseline (static rules):  ₹${(benchmarkData.baseline_recovery_paise / 100).toLocaleString()}
RecoveryOS (AI agent):    ₹${(benchmarkData.ai_recovery_paise / 100).toLocaleString()}
Uplift:                   +${benchmarkData.incremental_uplift_percent}%

Escalations to Review:    ${benchmarkData.escalations?.toLocaleString() ?? 'N/A'}
══════════════════════════════════════════════════════════════`}
                </div>
              </motion.div>
            )}
          </div>
        )}

        {/* ============ REVIEWS TAB ============ */}
        {activeTab === "reviews" && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Shield className="w-6 h-6 text-amber-500" />
                <h2 className="text-xl font-bold text-white">Escalation Queue</h2>
              </div>
              <button
                onClick={fetchReviews}
                disabled={reviewsLoading}
                className="flex items-center gap-2 bg-gray-800 hover:bg-gray-700 text-white px-4 py-2 rounded-lg text-sm transition disabled:opacity-50"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${reviewsLoading ? "animate-spin" : ""}`} />
                Refresh
              </button>
            </div>

            {reviews.length === 0 ? (
              <div className="bg-[#0A0E18] rounded-2xl border border-gray-800/60 py-16 text-center text-gray-600">
                <Shield className="w-10 h-10 mx-auto mb-3 opacity-20" />
                <p className="text-sm">No reviews in queue</p>
                <p className="text-xs mt-1 text-gray-700">Suspicious or high-value transactions appear here</p>
              </div>
            ) : (
              <div className="space-y-3">
                {reviews.map((review) => (
                  <motion.div
                    key={review.review_id}
                    initial={{ opacity: 0, y: 5 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="bg-[#0A0E18] rounded-xl border border-gray-800/60 p-5"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 space-y-3">
                        <div className="flex items-center gap-2">
                          <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded border ${review.status === "pending" ? "bg-amber-500/10 text-amber-400 border-amber-500/20" :
                            review.status === "approved" ? "bg-green-500/10 text-green-400 border-green-500/20" :
                              "bg-red-500/10 text-red-400 border-red-500/20"
                            }`}>
                            {review.status}
                          </span>
                          <span className="text-[11px] text-gray-600 font-mono">{review.review_id.slice(0, 16)}...</span>
                        </div>

                        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                          <div>
                            <span className="text-gray-600 block text-[10px] uppercase">Payment</span>
                            <span className="text-white font-mono">{review.payment_id}</span>
                          </div>
                          <div>
                            <span className="text-gray-600 block text-[10px] uppercase">Amount</span>
                            <span className="text-white font-bold">₹{(review.amount / 100).toLocaleString()}</span>
                          </div>
                          <div>
                            <span className="text-gray-600 block text-[10px] uppercase">Action</span>
                            <span className="text-blue-400">{review.action_type}</span>
                          </div>
                          <div>
                            <span className="text-gray-600 block text-[10px] uppercase">Confidence</span>
                            <span className="text-white">{(review.ai_confidence * 100).toFixed(0)}%</span>
                          </div>
                        </div>

                        <p className="text-xs text-amber-300/70">{review.policy_reason}</p>
                        {review.ai_diagnosis && (
                          <p className="text-[11px] text-gray-500 leading-relaxed">{review.ai_diagnosis.slice(0, 200)}{review.ai_diagnosis.length > 200 ? "..." : ""}</p>
                        )}
                      </div>

                      {review.status === "pending" && (
                        <div className="flex flex-col gap-1.5">
                          <button
                            onClick={() => handleApprove(review.review_id)}
                            className="flex items-center gap-1 bg-green-600 hover:bg-green-500 text-white px-3 py-1.5 rounded-lg text-xs font-medium transition"
                          >
                            <CheckCircle2 className="w-3 h-3" />
                            Approve
                          </button>
                          <button
                            onClick={() => handleReject(review.review_id)}
                            className="flex items-center gap-1 bg-red-600/70 hover:bg-red-500 text-white px-3 py-1.5 rounded-lg text-xs font-medium transition"
                          >
                            <XCircle className="w-3 h-3" />
                            Reject
                          </button>
                        </div>
                      )}
                    </div>
                  </motion.div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ============ AUDIT TAB ============ */}
        {activeTab === "audit" && (
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <Eye className="w-6 h-6 text-indigo-500" />
              <h2 className="text-xl font-bold text-white">Payment Audit Trail</h2>
            </div>

            <div className="flex gap-2">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-3 w-4 h-4 text-gray-600" />
                <input
                  type="text"
                  value={auditPaymentId}
                  onChange={(e) => setAuditPaymentId(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && fetchAuditTrail()}
                  placeholder="Enter payment ID (e.g. pay_abc123)"
                  className="w-full bg-[#0C1120] border border-gray-700/50 text-white rounded-lg pl-10 pr-3 py-2.5 text-sm focus:ring-1 focus:ring-indigo-500/50 outline-none font-mono"
                />
              </div>
              <button
                onClick={fetchAuditTrail}
                disabled={auditLoading || !auditPaymentId.trim()}
                className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-5 py-2.5 rounded-lg text-sm font-medium transition disabled:opacity-50"
              >
                {auditLoading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Search className="w-3.5 h-3.5" />}
                Lookup
              </button>
            </div>

            {auditTrail?.error && (
              <div className="bg-red-950/20 border border-red-900/30 text-red-300 p-3 rounded-lg text-sm">
                {auditTrail.error}
              </div>
            )}

            {auditTrail?.trail && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="bg-[#0A0E18] rounded-xl border border-gray-800/60 p-6">
                <p className="text-xs text-gray-500 mb-4">{auditTrail.total_entries} events for <span className="text-white font-mono">{auditTrail.payment_id}</span></p>

                <div className="relative pl-4 border-l-2 border-gray-800 space-y-4">
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
                      <div key={i} className="relative">
                        <div className={`absolute -left-[23px] top-0.5 w-4 h-4 rounded-full bg-[#0A0E18] border-2 border-gray-700 flex items-center justify-center`}>
                          <div className={`w-1.5 h-1.5 rounded-full ${config.color.replace("text-", "bg-")}`} />
                        </div>
                        <div className="ml-2">
                          <div className="flex items-baseline gap-2 mb-1">
                            <span className={`text-xs font-semibold ${config.color}`}>
                              {entry.event_type.replace(/_/g, " ")}
                            </span>
                            <span className="text-[10px] text-gray-600">
                              {entry.created_at ? new Date(entry.created_at).toLocaleString() : ""}
                            </span>
                          </div>
                          <pre className="text-[11px] text-gray-500 font-mono bg-[#060910] p-2.5 rounded-lg overflow-x-auto whitespace-pre-wrap break-all">
                            {JSON.stringify(entry.data, null, 2)}
                          </pre>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </motion.div>
            )}

            {!auditTrail && (
              <div className="bg-[#0A0E18] rounded-xl border border-gray-800/60 py-16 text-center text-gray-600">
                <Eye className="w-10 h-10 mx-auto mb-3 opacity-20" />
                <p className="text-sm">Enter a payment ID to view its complete audit trail</p>
                <p className="text-[11px] mt-1 text-gray-700">detection → AI diagnosis → policy → execution → reconciliation</p>
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  );
}
