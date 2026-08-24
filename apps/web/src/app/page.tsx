"use client";

import React, { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { motion, AnimatePresence } from "framer-motion";
import {
  Activity, ShieldAlert, CheckCircle, RefreshCw,
  Zap, Play, BarChart3, Database, Shield, Clock, Eye, XCircle,
  CheckCircle2, AlertTriangle, ChevronDown, ChevronRight,
  ArrowRight, CreditCard, TrendingUp, Search, Wallet,
  CircleDollarSign, Lock, Sparkles, Ban, User,
  Link as LinkIcon, Cpu, ShieldCheck, Box, Package, WalletCards, StopCircle
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

const FAILURE_REASONS = [
  { value: "insufficient_funds", label: "Insufficient Funds", emoji: <WalletCards className="w-4 h-4" /> },
  { value: "temporary_network_timeout", label: "Network Timeout", emoji: <Activity className="w-4 h-4" /> },
  { value: "suspected_fraud", label: "Suspected Fraud", emoji: <ShieldAlert className="w-4 h-4" /> },
  { value: "card_expired", label: "Card Expired", emoji: <Clock className="w-4 h-4" /> },
];

const spring = { type: "spring", stiffness: 300, damping: 28 };
const stagger = { staggerChildren: 0.08, delayChildren: 0.1 };

export default function RecoveryOSDashboard() {
  const [activeTab, setActiveTab] = useState<"live" | "benchmark" | "reviews" | "audit">("live");

  const [pipelineStage, setPipelineStage] = useState<PipelineStage>("idle");
  const [pipelineResult, setPipelineResult] = useState<PipelineResult>(null);
  const [pipelineCards, setPipelineCards] = useState<{ key: string; title: string; detail: string; color: string; icon: React.ReactNode }[]>([]);
  const [isRecovering, setIsRecovering] = useState(false);

  const [amount, setAmount] = useState<number>(499);
  const [simulateMode, setSimulateMode] = useState(false);
  const [failureReason, setFailureReason] = useState("insufficient_funds");

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
      const res = await axios.get(`${API_BASE}/analytics/summary`);
      setAnalytics(res.data);
      if (res.data.recent_transactions) setRecentTxns(res.data.recent_transactions);
    } catch { }
  }, []);

  useEffect(() => {
    fetchAnalytics();
    const iv = setInterval(fetchAnalytics, 8000);
    return () => clearInterval(iv);
  }, [fetchAnalytics]);

  const delay = (ms: number) => new Promise(r => setTimeout(r, ms));

  const addPipelineCard = (key: string, title: string, detail: string, color: string, icon: React.ReactNode) => {
    setPipelineCards(prev => [...prev, { key, title, detail, color, icon }]);
  };

  const handlePay = async () => {
    if (simulateMode) {
      await runSimulatedRecovery();
    } else {
      await runRealPayment();
    }
  };

  const runRealPayment = async () => {
    setIsRecovering(true);
    setPipelineStage("detect");
    setPipelineResult(null);
    setPipelineCards([]);

    let hasTriggeredRecovery = false;
    let localFailures = 0;
    const amountPaise = amount * 100;
    addPipelineCard("init", "Payment Initiated", `₹${amount} via Razorpay Checkout`, "blue", <CreditCard className="w-5 h-5 text-blue-500" />);

    try {
      const orderRes = await axios.post(`${API_BASE}/recoveries/create-order?amount=${amountPaise}`);
      const { order_id, amount: orderAmount, key_id } = orderRes.data;

      addPipelineCard("order", "Order Created", `Razorpay Order: ${order_id}`, "blue", <Package className="w-5 h-5 text-blue-500" />);

      const options = {
        key: key_id,
        amount: orderAmount,
        currency: "INR",
        name: "RecoveryOS Demo",
        description: "Test Payment for AI Recovery Demo",
        order_id: order_id,
        handler: async function (response: any) {
          if (hasTriggeredRecovery) return;
          hasTriggeredRecovery = true;
          setPipelineStage("result");
          setPipelineResult("success");
          addPipelineCard("success", "Payment Successful", `Payment ID: ${response.razorpay_payment_id}`, "green", <CheckCircle2 className="w-5 h-5 text-emerald-500" />);
          setIsRecovering(false);

          try {
            await axios.post(`${API_BASE}/audit/log-success`, {
              payment_id: response.razorpay_payment_id,
              amount: amountPaise,
            });
          } catch { }

          fetchAnalytics();
        },
        modal: {
          ondismiss: function () {
            if (hasTriggeredRecovery) return;
            hasTriggeredRecovery = true;
            setPipelineStage("detect");
            addPipelineCard("dismissed", "Checkout Dismissed", "Customer closed the payment window — triggering AI recovery", "amber", <AlertTriangle className="w-5 h-5 text-amber-500" />);
            triggerRecoveryFromDismissal(amountPaise);
          },
        },
        theme: { color: "#2563eb" },
      };

      const rzp = new (window as any).Razorpay(options);
      rzp.on("payment.failed", function (response: any) {
        localFailures++;
        if (localFailures > 2) {
          rzp.close();
          addPipelineCard("error", "Max Retries Exceeded", "Razorpay Checkout closed automatically after 3 failed attempts.", "red", <Ban className="w-5 h-5 text-red-500" />);
        }

        if (hasTriggeredRecovery) return;
        hasTriggeredRecovery = true;
        const reason = response.error?.description || "unknown_error";
        setPipelineStage("detect");
        addPipelineCard("failed", "Payment Failed", `Reason: ${reason}`, "red", <XCircle className="w-5 h-5 text-red-500" />);
        triggerRecoveryForPayment(amountPaise, "insufficient_funds");
      });
      rzp.open();
    } catch (error: any) {
      addPipelineCard("error", "Order Creation Failed", error.message || "Could not create Razorpay order", "red", <XCircle className="w-5 h-5 text-red-500" />);
      setPipelineStage("result");
      setPipelineResult("error");
      setIsRecovering(false);
    }
  };

  const triggerRecoveryFromDismissal = async (amountPaise: number) => {
    await triggerRecoveryForPayment(amountPaise, "checkout_abandoned");
  };

  const triggerRecoveryForPayment = async (amountPaise: number, reason: string, retryCount: number = 0) => {
    const paymentId = `pay_${Math.random().toString(36).substring(2, 10)}`;
    setPipelineStage("diagnose");
    addPipelineCard("diagnose", "AI Agent Activated", "Gemini 2.5 Flash analyzing failure pattern...", "indigo", <Cpu className="w-5 h-5 text-indigo-500" />);

    try {
      const res = await axios.post(`${API_BASE}/recoveries/execute`, {
        payment_id: paymentId,
        customer_id: `cust_${Math.random().toString(36).substring(2, 6)}`,
        amount: amountPaise,
        failure_reason: reason,
        retry_count: retryCount,
      });
      const data = res.data;

      await delay(400);
      setPipelineStage("policy");

      if (data.status === "escalated") {
        addPipelineCard("policy", "Policy: Human Review Required", data.message, "red", <ShieldAlert className="w-5 h-5 text-red-500" />);
        await delay(400);
        setPipelineStage("result");
        setPipelineResult("escalated");
        addPipelineCard("result", "Escalated to Review Queue", `Review ID: ${data.provider_reference?.slice(0, 20)}...`, "red", <User className="w-5 h-5 text-red-500" />);
      } else if (data.status === "failed") {
        addPipelineCard("policy", "Policy: Blocked", data.message, "red", <StopCircle className="w-5 h-5 text-red-500" />);
        await delay(300);
        setPipelineStage("result");
        setPipelineResult("blocked");
        addPipelineCard("result", "Recovery Stopped", "Stopping rule or policy violation", "red", <Ban className="w-5 h-5 text-red-500" />);
      } else {
        addPipelineCard("policy", "Policy: Approved", "All safety checks passed", "green", <ShieldCheck className="w-5 h-5 text-emerald-500" />);
        await delay(400);
        setPipelineStage("execute");
        addPipelineCard("execute", "Razorpay Order Created", `Ref: ${data.provider_reference || data.execution_id.slice(0, 20)}`, "blue", <LinkIcon className="w-5 h-5 text-blue-500" />);
        await delay(300);
        setPipelineStage("result");
        setPipelineResult("success");
        addPipelineCard("result", "Recovery Initiated", `Action: ${data.action_type}`, "green", <Sparkles className="w-5 h-5 text-emerald-500" />);
      }
      fetchAnalytics();
    } catch (error: any) {
      setPipelineStage("result");
      setPipelineResult("error");
      addPipelineCard("error", "System Error", error.response?.data?.detail || error.message, "red", <XCircle className="w-5 h-5 text-red-500" />);
    } finally {
      setIsRecovering(false);
    }
  };

  const runSimulatedRecovery = async () => {
    setIsRecovering(true);
    setPipelineStage("detect");
    setPipelineResult(null);
    setPipelineCards([]);

    const paymentId = `pay_${Math.random().toString(36).substring(2, 10)}`;
    const amountPaise = amount * 100;
    const reasonInfo = FAILURE_REASONS.find(r => r.value === failureReason);

    addPipelineCard("detect", "Failure Detected", `₹${amount} (${paymentId})`, "amber", <AlertTriangle className="w-5 h-5 text-amber-500" />);
    await delay(500);

    setPipelineStage("diagnose");
    addPipelineCard("diagnose", "AI Agent Analyzing", "Gemini 2.5 Flash evaluating recovery probability...", "indigo", <Cpu className="w-5 h-5 text-indigo-500" />);

    try {
      const res = await axios.post(`${API_BASE}/recoveries/execute`, {
        payment_id: paymentId,
        customer_id: `cust_demo_${Math.random().toString(36).substring(2, 6)}`,
        amount: amountPaise,
        failure_reason: failureReason,
      });
      const data = res.data;

      await delay(400);
      setPipelineStage("policy");

      if (data.status === "escalated") {
        addPipelineCard("policy", "Policy: Requires Approval", data.message, "red", <ShieldAlert className="w-5 h-5 text-red-500" />);
        await delay(400);
        setPipelineStage("result");
        setPipelineResult("escalated");
        addPipelineCard("result", "Escalated to Human Review", `Review: ${data.provider_reference?.slice(0, 20)}...`, "red", <User className="w-5 h-5 text-red-500" />);
      } else if (data.status === "failed") {
        addPipelineCard("policy", "Policy: Blocked", data.message, "red", <StopCircle className="w-5 h-5 text-red-500" />);
        await delay(300);
        setPipelineStage("result");
        setPipelineResult("blocked");
        addPipelineCard("result", "Recovery Denied", "Stopping rule triggered", "red", <Ban className="w-5 h-5 text-red-500" />);
      } else {
        addPipelineCard("policy", "Policy: Approved", "Safety boundary cleared", "green", <ShieldCheck className="w-5 h-5 text-emerald-500" />);
        await delay(400);
        setPipelineStage("execute");
        addPipelineCard("execute", "Executing via Razorpay", `Order: ${data.provider_reference || "created"}`, "blue", <LinkIcon className="w-5 h-5 text-blue-500" />);
        await delay(300);
        setPipelineStage("result");
        setPipelineResult("success");
        addPipelineCard("result", "Recovery Successful", `${data.action_type} → ${data.provider_reference || data.execution_id.slice(0, 16)}`, "green", <Sparkles className="w-5 h-5 text-emerald-500" />);
      }
      fetchAnalytics();
    } catch (error: any) {
      setPipelineStage("result");
      setPipelineResult("error");
      addPipelineCard("error", "Error", error.response?.data?.detail || error.message, "red", <XCircle className="w-5 h-5 text-red-500" />);
    } finally {
      setIsRecovering(false);
    }
  };

  const toggleTxnAudit = async (paymentId: string) => {
    if (expandedTxn === paymentId) { setExpandedTxn(null); return; }
    setExpandedTxn(paymentId);
    if (!txnAudit[paymentId]) {
      try {
        const res = await axios.get(`${API_BASE}/audit/${paymentId}`);
        setTxnAudit(prev => ({ ...prev, [paymentId]: res.data }));
      } catch {
        setTxnAudit(prev => ({ ...prev, [paymentId]: { error: "No audit trail found" } }));
      }
    }
  };

  const runBenchmark = async () => {
    setIsSimulating(true);
    try {
      const res = await axios.post(`${API_BASE}/analytics/simulate-benchmark`);
      setBenchmarkData(res.data);
    } catch { } finally { setIsSimulating(false); }
  };

  const fetchReviews = async () => {
    setReviewsLoading(true);
    try {
      const res = await axios.get(`${API_BASE}/reviews?status=all`);
      setReviews(res.data.reviews || []);
    } catch { } finally { setReviewsLoading(false); }
  };

  const handleApprove = async (id: string) => {
    try { await axios.post(`${API_BASE}/reviews/${id}/approve`); fetchReviews(); fetchAnalytics(); } catch { }
  };

  const handleReject = async (id: string) => {
    try { await axios.post(`${API_BASE}/reviews/${id}/reject`); fetchReviews(); } catch { }
  };

  const fetchAuditTrail = async () => {
    if (!auditPaymentId.trim()) return;
    setAuditLoading(true);
    try {
      const res = await axios.get(`${API_BASE}/audit/${auditPaymentId}`);
      setAuditTrail(res.data);
    } catch (e: any) {
      setAuditTrail({ error: e.response?.data?.detail || "Not found" });
    } finally { setAuditLoading(false); }
  };

  const cardColors: Record<string, string> = {
    blue: "border-blue-200 bg-blue-50/80",
    green: "border-emerald-200 bg-emerald-50/80",
    amber: "border-amber-200 bg-amber-50/80",
    red: "border-red-200 bg-red-50/80",
    indigo: "border-indigo-200 bg-indigo-50/80",
  };

  const cardTextColors: Record<string, string> = {
    blue: "text-blue-700",
    green: "text-emerald-700",
    amber: "text-amber-700",
    red: "text-red-700",
    indigo: "text-indigo-700",
  };

  const tabs = [
    { key: "live", label: "Live Recovery", icon: Zap },
    { key: "benchmark", label: "50k Benchmark", icon: BarChart3 },
    { key: "reviews", label: "Escalation Queue", icon: Shield },
    { key: "audit", label: "Audit Trail", icon: Eye },
  ];

  return (
    <div className="min-h-screen bg-[#fafbfc]">
      <div className="max-w-6xl mx-auto px-4 md:px-8 py-6 space-y-5">

        <header className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="relative">
              <div className="bg-gradient-to-br from-blue-600 to-indigo-700 p-2.5 rounded-xl shadow-md shadow-blue-200">
                <Zap className="w-6 h-6 text-white" />
              </div>
              <div className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 bg-green-500 rounded-full border-2 border-[#fafbfc]" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-gray-900">RecoveryOS</h1>
              <p className="text-xs text-blue-600 font-medium">Razorpay AI Buildathon · Track 03</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 text-[11px] font-medium text-emerald-700 bg-emerald-50 border border-emerald-200 px-2.5 py-1 rounded-full">
              <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse" />
              Live
            </span>
            <span className="inline-flex items-center gap-1.5 text-[11px] font-medium text-blue-700 bg-blue-50 border border-blue-200 px-2.5 py-1 rounded-full">
              <CreditCard className="w-3 h-3" />
              Razorpay Test
            </span>
            <span className="inline-flex items-center gap-1.5 text-[11px] font-medium text-purple-700 bg-purple-50 border border-purple-200 px-2.5 py-1 rounded-full">
              <Sparkles className="w-3 h-3" />
              Gemini 2.5 Flash
            </span>
          </div>
        </header>

        <nav className="flex gap-1 bg-white p-1 rounded-xl border border-gray-200 shadow-sm">
          {tabs.map(tab => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.key}
                onClick={() => { setActiveTab(tab.key as any); if (tab.key === "reviews") fetchReviews(); }}
                className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-all ${activeTab === tab.key
                  ? "bg-blue-600 text-white shadow-sm"
                  : "text-gray-500 hover:text-gray-800 hover:bg-gray-50"
                  }`}
              >
                <Icon className="w-3.5 h-3.5" />
                {tab.label}
              </button>
            );
          })}
        </nav>

        {activeTab === "live" && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-5">

            <motion.div variants={{ show: stagger }} initial="hidden" animate="show" className="grid grid-cols-2 md:grid-cols-5 gap-3">
              {[
                { label: "Total Runs", value: analytics?.total_executions ?? "—", icon: Activity, iconColor: "text-blue-500", bg: "bg-blue-50" },
                { label: "Recovered", value: analytics?.successful_recoveries ?? "—", icon: CheckCircle, iconColor: "text-emerald-500", bg: "bg-emerald-50" },
                { label: "Blocked", value: analytics?.failed_recoveries ?? "—", icon: Ban, iconColor: "text-red-500", bg: "bg-red-50" },
                { label: "In Review", value: analytics?.pending_reviews ?? "—", icon: ShieldAlert, iconColor: "text-amber-500", bg: "bg-amber-50" },
                { label: "Recovery Rate", value: `${analytics?.recovery_rate_percent ?? "—"}%`, icon: TrendingUp, iconColor: "text-indigo-500", bg: "bg-indigo-50" },
              ].map(m => {
                const Icon = m.icon;
                return (
                  <motion.div
                    key={m.label}
                    variants={{ hidden: { opacity: 0, y: 12 }, show: { opacity: 1, y: 0 } }}
                    transition={spring}
                    className="glass-card rounded-xl p-4"
                  >
                    <div className="flex items-center gap-2 mb-1.5">
                      <div className={`w-7 h-7 rounded-lg ${m.bg} flex items-center justify-center`}>
                        <Icon className={`w-3.5 h-3.5 ${m.iconColor}`} />
                      </div>
                      <span className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider">{m.label}</span>
                    </div>
                    <p className="text-2xl font-bold text-gray-900">{m.value}</p>
                  </motion.div>
                );
              })}
            </motion.div>

            <div className="grid grid-cols-1 lg:grid-cols-5 gap-5">

              <div className="lg:col-span-2">
                <div className="payment-card">
                  <div className="flex items-center justify-between mb-6">
                    <div className="flex items-center gap-2">
                      <Wallet className="w-5 h-5 text-blue-600" />
                      <span className="text-sm font-bold text-gray-900">
                        {simulateMode ? "Failure Simulation" : "Payment"}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] text-gray-500 uppercase font-semibold">{simulateMode ? "Test" : "Real"}</span>
                      <button
                        onClick={() => setSimulateMode(!simulateMode)}
                        className={`relative w-10 h-5 rounded-full transition-colors ${simulateMode ? "bg-amber-500" : "bg-blue-600"}`}
                      >
                        <motion.div
                          layout
                          transition={spring}
                          className="absolute top-0.5 w-4 h-4 rounded-full bg-white shadow-sm"
                          style={{ left: simulateMode ? "calc(100% - 18px)" : "2px" }}
                        />
                      </button>
                    </div>
                  </div>

                  <div className="mb-6">
                    <div className="flex gap-1 mb-4">
                      {[...Array(4)].map((_, g) => (
                        <div key={g} className="flex gap-1">
                          {g < 3 ? (
                            [...Array(4)].map((_, i) => (
                              <span key={i} className="text-lg text-gray-300">•</span>
                            ))
                          ) : (
                            <span className="text-lg text-gray-800 tracking-widest font-mono font-medium">1221</span>
                          )}
                        </div>
                      ))}
                    </div>
                    <div className="flex justify-between items-end">
                      <div>
                        <p className="text-[10px] text-gray-400 uppercase mb-0.5 font-semibold">Card Holder</p>
                        <p className="text-sm text-gray-800 font-bold">Test User</p>
                      </div>
                      <div>
                        <p className="text-[10px] text-gray-400 uppercase mb-0.5 font-semibold">Expires</p>
                        <p className="text-sm text-gray-800 font-bold">12/27</p>
                      </div>
                    </div>
                  </div>

                  <div className="mb-4">
                    <label className="text-[10px] text-gray-500 uppercase font-bold mb-1.5 block">Amount (₹)</label>
                    <div className="relative">
                      <span className="absolute left-3 top-2.5 text-gray-500 font-medium text-lg">₹</span>
                      <input
                        type="number"
                        value={amount}
                        onChange={e => setAmount(Number(e.target.value))}
                        className="w-full bg-gray-50 border border-gray-200 text-gray-900 rounded-xl pl-8 pr-3 py-2.5 text-lg font-bold focus:ring-2 focus:ring-blue-500/50 outline-none placeholder:text-gray-400 shadow-sm"
                        min="1"
                        required
                      />
                    </div>
                  </div>

                  <AnimatePresence>
                    {simulateMode && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        className="mb-4 overflow-hidden"
                      >
                        <label className="text-[10px] text-gray-500 uppercase font-bold mb-1.5 block">Failure Reason</label>
                        <div className="grid grid-cols-2 gap-1.5">
                          {FAILURE_REASONS.map(r => (
                            <button
                              key={r.value}
                              onClick={() => setFailureReason(r.value)}
                              className={`text-left px-3 py-2 rounded-lg text-xs font-semibold transition-all ${failureReason === r.value
                                ? "bg-amber-100 text-amber-800 border border-amber-200"
                                : "bg-gray-50 text-gray-600 border border-gray-200 hover:bg-gray-100"
                                }`}
                            >
                              <span className="mr-1">{r.emoji}</span> {r.label}
                            </button>
                          ))}
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>

                  <button
                    onClick={handlePay}
                    disabled={isRecovering || amount <= 0}
                    className="w-full flex items-center justify-center gap-2 bg-blue-600 text-white font-bold py-3.5 px-4 rounded-xl transition-all hover:bg-blue-700 disabled:opacity-50 shadow-md shadow-blue-500/20 text-base"
                  >
                    {isRecovering ? (
                      <><RefreshCw className="w-5 h-5 animate-spin" /> Processing...</>
                    ) : simulateMode ? (
                      <><AlertTriangle className="w-5 h-5" /> Simulate Failure — ₹{amount}</>
                    ) : (
                      <><Lock className="w-5 h-5" /> Pay ₹{amount.toLocaleString()}</>
                    )}
                  </button>

                  {!simulateMode && (
                    <p className="text-[10px] text-gray-400 font-medium text-center mt-3">Opens Razorpay Checkout (Test Mode)</p>
                  )}
                </div>
              </div>

              <div className="lg:col-span-3">
                <div className="glass-card rounded-2xl p-5 min-h-[420px] max-h-[500px] flex flex-col">
                  <div className="flex items-center gap-2 mb-4">
                    <div className="w-2 h-2 rounded-full bg-blue-500" />
                    <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Recovery Pipeline</h3>
                    {pipelineStage !== "idle" && !isRecovering && (
                      <button
                        onClick={() => { setPipelineStage("idle"); setPipelineResult(null); setPipelineCards([]); }}
                        className="ml-auto text-[10px] text-gray-400 hover:text-gray-600 underline"
                      >
                        Clear
                      </button>
                    )}
                  </div>

                  {pipelineStage === "idle" ? (
                    <div className="flex-1 flex flex-col items-center justify-center text-gray-400">
                      <motion.div
                        animate={{ y: [0, -6, 0] }}
                        transition={{ duration: 2.5, repeat: Infinity, ease: "easeInOut" }}
                      >
                        <CircleDollarSign className="w-12 h-12 text-gray-300 mb-3" />
                      </motion.div>
                      <p className="text-sm font-medium text-gray-500">Make a payment to see the pipeline in action</p>
                      <p className="text-xs text-gray-400 mt-1">Toggle "Test" mode to simulate specific failures</p>
                    </div>
                  ) : (
                    <div className="flex-1 space-y-2 overflow-y-auto">
                      <AnimatePresence mode="popLayout">
                        {pipelineCards.map((card, i) => (
                          <motion.div
                            key={`${card.key}-${i}`}
                            initial={{ opacity: 0, x: -20, scale: 0.95 }}
                            animate={{ opacity: 1, x: 0, scale: 1 }}
                            exit={{ opacity: 0, scale: 0.9 }}
                            transition={{ ...spring, delay: 0.05 }}
                            className={`flex items-start gap-3 p-3 rounded-xl border ${cardColors[card.color] || cardColors.blue}`}
                          >
                            <span className="text-xl flex-shrink-0 mt-0.5">{card.icon}</span>
                            <div className="flex-1 min-w-0">
                              <p className={`text-sm font-semibold ${cardTextColors[card.color] || "text-gray-700"}`}>
                                {card.title}
                              </p>
                              <p className="text-xs text-gray-500 mt-0.5 break-all">{card.detail}</p>
                            </div>
                            {i === pipelineCards.length - 1 && isRecovering && (
                              <RefreshCw className="w-4 h-4 text-gray-400 animate-spin flex-shrink-0 mt-1" />
                            )}
                          </motion.div>
                        ))}
                      </AnimatePresence>

                      <AnimatePresence>
                        {pipelineResult && !isRecovering && (
                          <motion.div
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={spring}
                            className={`mt-3 p-3 rounded-xl text-center font-semibold text-sm ${pipelineResult === "success" ? "bg-emerald-100 text-emerald-800 border border-emerald-200" :
                              pipelineResult === "escalated" ? "bg-red-100 text-red-800 border border-red-200" :
                                "bg-red-100 text-red-800 border border-red-200"
                              }`}
                          >
                            <div className="flex items-center justify-center gap-2">
                              {pipelineResult === "success" && <><CheckCircle2 className="w-5 h-5" /> Recovery pipeline completed successfully</>}
                              {pipelineResult === "escalated" && <><ShieldAlert className="w-5 h-5" /> Escalated to human review queue</>}
                              {pipelineResult === "blocked" && <><StopCircle className="w-5 h-5" /> Blocked by policy engine</>}
                              {pipelineResult === "error" && <><XCircle className="w-5 h-5" /> Pipeline encountered an error</>}
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </div>
                  )}
                </div>
              </div>
            </div>

            <div className="glass-card rounded-2xl overflow-hidden">
              <div className="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Clock className="w-4 h-4 text-gray-400" />
                  <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Recent Transactions</h3>
                </div>
                <span className="text-[10px] text-gray-400">{recentTxns.length} records</span>
              </div>

              {recentTxns.length === 0 ? (
                <div className="py-12 text-center text-gray-400">
                  <Database className="w-8 h-8 mx-auto mb-2 text-gray-300" />
                  <p className="text-sm">No transactions yet</p>
                </div>
              ) : (
                <div className="divide-y divide-gray-100 max-h-64 overflow-y-auto">
                  {recentTxns.map(txn => {
                    const isExp = expandedTxn === txn.payment_id;
                    const sc: Record<string, string> = {
                      STARTED: "bg-emerald-100 text-emerald-700",
                      SUCCEEDED: "bg-emerald-100 text-emerald-700",
                      FAILED: "bg-red-100 text-red-700",
                    };
                    return (
                      <div key={txn.execution_id}>
                        <button
                          onClick={() => toggleTxnAudit(txn.payment_id)}
                          className="w-full px-5 py-3 flex items-center gap-3 hover:bg-gray-50/80 transition text-left"
                        >
                          {isExp ? <ChevronDown className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" /> : <ChevronRight className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />}
                          <span className="text-xs font-mono text-gray-500 w-24 flex-shrink-0">{txn.payment_id}</span>
                          <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${sc[txn.status] || "bg-gray-100 text-gray-600"}`}>{txn.status}</span>
                          <span className="text-xs text-gray-500 flex-1 truncate">{txn.message}</span>
                          <span className="text-[10px] text-gray-400 flex-shrink-0">{txn.created_at ? new Date(txn.created_at).toLocaleTimeString() : ""}</span>
                        </button>
                        <AnimatePresence>
                          {isExp && (
                            <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.2 }} className="overflow-hidden">
                              <div className="px-5 pb-4 pl-14">
                                {txnAudit[txn.payment_id]?.error ? (
                                  <p className="text-xs text-gray-400 italic">{txnAudit[txn.payment_id].error}</p>
                                ) : txnAudit[txn.payment_id]?.trail ? (
                                  <div className="relative pl-4 border-l-2 border-gray-200 space-y-2">
                                    {txnAudit[txn.payment_id].trail.map((e: any, i: number) => {
                                      const ec: Record<string, string> = { failure_detected: "text-amber-600", ai_diagnosis: "text-blue-600", policy_decision: "text-indigo-600", execution_succeeded: "text-emerald-600", execution_failed: "text-red-600", escalated_to_review: "text-amber-600", review_approved: "text-emerald-600", review_rejected: "text-red-600", stopping_rule_triggered: "text-red-600" };
                                      return (
                                        <div key={i} className="relative">
                                          <div className="absolute -left-[13px] top-1.5 w-2 h-2 rounded-full bg-white border-2 border-gray-300" />
                                          <p className={`text-[11px] font-semibold ${ec[e.event_type] || "text-gray-500"}`}>{e.event_type.replace(/_/g, " ")}</p>
                                          <pre className="text-[10px] text-gray-400 mt-0.5 font-mono whitespace-pre-wrap break-all bg-gray-50 p-2 rounded">{JSON.stringify(e.data, null, 1)}</pre>
                                        </div>
                                      );
                                    })}
                                  </div>
                                ) : (
                                  <div className="flex items-center gap-2 text-xs text-gray-400"><RefreshCw className="w-3 h-3 animate-spin" /> Loading...</div>
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
          </motion.div>
        )}

        {activeTab === "benchmark" && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="glass-card rounded-2xl p-6">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2"><BarChart3 className="w-6 h-6 text-blue-500" /> 50,000 Event Evaluation</h2>
                <p className="text-xs text-gray-400 mt-1">Synthetic batch processed through Policy Engine</p>
              </div>
              <button onClick={runBenchmark} disabled={isSimulating} className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-5 py-2 rounded-lg text-sm font-medium transition disabled:opacity-50 shadow-sm">
                {isSimulating ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                {isSimulating ? "Running..." : "Run Simulation"}
              </button>
            </div>

            {!benchmarkData && !isSimulating && (
              <div className="py-16 text-center text-gray-400">
                <Database className="w-10 h-10 mx-auto mb-3 text-gray-300" />
                <p className="text-sm">Run simulation to evaluate against 50k synthetic payment failures</p>
              </div>
            )}

            {isSimulating && (
              <div className="py-16 text-center text-blue-500">
                <RefreshCw className="w-10 h-10 mx-auto mb-3 animate-spin text-blue-400" />
                <p className="animate-pulse text-sm">Processing events through Policy Engine...</p>
              </div>
            )}

            {benchmarkData && !isSimulating && (
              <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
                <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-5">
                  {[
                    { label: "Baseline", value: `₹${(benchmarkData.baseline_recovery_paise / 100).toLocaleString()}`, color: "text-gray-700" },
                    { label: "AI Recovery", value: `₹${(benchmarkData.ai_recovery_paise / 100).toLocaleString()}`, color: "text-emerald-600" },
                    { label: "Uplift", value: `+${benchmarkData.incremental_uplift_percent}%`, color: "text-blue-600" },
                    { label: "Policy Blocks", value: benchmarkData.policy_blocks.toLocaleString(), color: "text-amber-600" },
                    { label: "Unsafe Rate", value: `${benchmarkData.unsafe_action_rate}%`, color: "text-emerald-600" },
                  ].map(m => (
                    <div key={m.label} className="bg-gray-50 p-4 rounded-xl border border-gray-100">
                      <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-1">{m.label}</p>
                      <p className={`text-lg font-mono font-bold ${m.color}`}>{m.value}</p>
                    </div>
                  ))}
                </div>
                <div className="bg-gray-900 text-gray-300 p-5 rounded-xl font-mono text-xs leading-relaxed overflow-x-auto whitespace-pre">
                  {`═══ RECOVERYOS EVALUATION ══════════════════════════════
Events: ${benchmarkData.total_events.toLocaleString()}  |  Unsafe: ${benchmarkData.unsafe_action_rate}%

Baseline (static rules):  ₹${(benchmarkData.baseline_recovery_paise / 100).toLocaleString()}
RecoveryOS (AI agent):    ₹${(benchmarkData.ai_recovery_paise / 100).toLocaleString()}
Uplift:                   +${benchmarkData.incremental_uplift_percent}%
Escalations:              ${benchmarkData.escalations?.toLocaleString() ?? "N/A"}
Policy Blocks:            ${benchmarkData.policy_blocks.toLocaleString()}
════════════════════════════════════════════════════════`}
                </div>

                <div className="mt-6 bg-blue-50 border border-blue-100 rounded-xl p-5">
                  <h4 className="text-sm font-bold text-blue-900 flex items-center gap-2 mb-3">
                    <Sparkles className="w-4 h-4 text-blue-600" /> What do these numbers mean?
                  </h4>
                  <ul className="text-xs text-blue-800 space-y-2.5 leading-relaxed">
                    <li><strong className="text-blue-950 font-semibold">Baseline:</strong> The revenue a traditional payment gateway recovers using basic, "dumb" retries (e.g., just trying the card again).</li>
                    <li><strong className="text-blue-950 font-semibold">AI Recovery:</strong> The revenue recovered by our intelligent agent. It understands the <em>context</em> of the failure and uses dynamic interventions (like sending an SMS link for network timeouts, or alerting a human for fraud).</li>
                    <li><strong className="text-blue-950 font-semibold">Uplift:</strong> The percentage increase in money saved by using the AI Agent instead of static rules.</li>
                    <li><strong className="text-blue-950 font-semibold">Policy Blocks:</strong> Actions the AI attempted that were blocked by our Safety Engine to prevent bad user experiences or compliance violations.</li>
                    <li><strong className="text-blue-950 font-semibold">Unsafe Rate:</strong> The percentage of actions that violated core safety boundaries. <span className="font-semibold text-emerald-700 bg-emerald-100 px-1.5 py-0.5 rounded">{benchmarkData.unsafe_action_rate}%</span> means the agent operated completely safely at scale.</li>
                  </ul>
                </div>
              </motion.div>
            )}
          </motion.div>
        )}

        {activeTab === "reviews" && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2"><Shield className="w-6 h-6 text-amber-500" /> Escalation Queue</h2>
              <button onClick={fetchReviews} disabled={reviewsLoading} className="flex items-center gap-2 bg-white border border-gray-200 hover:bg-gray-50 text-gray-700 px-4 py-2 rounded-lg text-sm transition disabled:opacity-50 shadow-sm">
                <RefreshCw className={`w-3.5 h-3.5 ${reviewsLoading ? "animate-spin" : ""}`} /> Refresh
              </button>
            </div>

            {reviews.length === 0 ? (
              <div className="glass-card rounded-2xl py-16 text-center text-gray-400">
                <Shield className="w-10 h-10 mx-auto mb-3 text-gray-300" />
                <p className="text-sm">No reviews in queue</p>
                <p className="text-xs mt-1 text-gray-400">Try simulating a "Suspected Fraud" failure</p>
              </div>
            ) : (
              <div className="space-y-3">
                {reviews.map(rev => (
                  <motion.div key={rev.review_id} initial={{ opacity: 0, y: 5 }} animate={{ opacity: 1, y: 0 }} className="glass-card rounded-xl p-5">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 space-y-2">
                        <div className="flex items-center gap-2">
                          <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${rev.status === "pending" ? "bg-amber-100 text-amber-700" :
                            rev.status === "approved" ? "bg-emerald-100 text-emerald-700" : "bg-red-100 text-red-700"
                            }`}>{rev.status}</span>
                          <span className="text-[11px] text-gray-400 font-mono">{rev.review_id.slice(0, 16)}...</span>
                        </div>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                          <div><span className="text-gray-400 block text-[10px] uppercase">Payment</span><span className="text-gray-800 font-mono">{rev.payment_id}</span></div>
                          <div><span className="text-gray-400 block text-[10px] uppercase">Amount</span><span className="text-gray-900 font-bold">₹{(rev.amount / 100).toLocaleString()}</span></div>
                          <div><span className="text-gray-400 block text-[10px] uppercase">Action</span><span className="text-blue-600">{rev.action_type}</span></div>
                          <div><span className="text-gray-400 block text-[10px] uppercase">Confidence</span><span className="text-gray-800">{(rev.ai_confidence * 100).toFixed(0)}%</span></div>
                        </div>
                        <p className="text-xs text-amber-600">{rev.policy_reason}</p>
                        {rev.ai_diagnosis && <p className="text-[11px] text-gray-500 leading-relaxed">{rev.ai_diagnosis.slice(0, 200)}{rev.ai_diagnosis.length > 200 ? "..." : ""}</p>}
                      </div>
                      {rev.status === "pending" && (
                        <div className="flex flex-col gap-1.5">
                          <button onClick={() => handleApprove(rev.review_id)} className="flex items-center gap-1 bg-emerald-600 hover:bg-emerald-700 text-white px-3 py-1.5 rounded-lg text-xs font-medium transition shadow-sm"><CheckCircle2 className="w-3 h-3" /> Approve</button>
                          <button onClick={() => handleReject(rev.review_id)} className="flex items-center gap-1 bg-red-100 hover:bg-red-200 text-red-700 px-3 py-1.5 rounded-lg text-xs font-medium transition"><XCircle className="w-3 h-3" /> Reject</button>
                        </div>
                      )}
                    </div>
                  </motion.div>
                ))}
              </div>
            )}
          </motion.div>
        )}

        {activeTab === "audit" && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-4">
            <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2"><Eye className="w-6 h-6 text-indigo-500" /> Payment Audit Trail</h2>

            <div className="flex gap-2">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-2.5 w-4 h-4 text-gray-400" />
                <input type="text" value={auditPaymentId} onChange={e => setAuditPaymentId(e.target.value)} onKeyDown={e => e.key === "Enter" && fetchAuditTrail()} placeholder="Enter payment ID (e.g. pay_abc123)" className="w-full bg-white border border-gray-200 text-gray-900 rounded-xl pl-10 pr-3 py-2.5 text-sm focus:ring-2 focus:ring-blue-500/30 focus:border-blue-400 outline-none font-mono shadow-sm" />
              </div>
              <button onClick={fetchAuditTrail} disabled={auditLoading || !auditPaymentId.trim()} className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white px-5 py-2.5 rounded-xl text-sm font-medium transition disabled:opacity-50 shadow-sm">
                {auditLoading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Search className="w-3.5 h-3.5" />} Lookup
              </button>
            </div>

            {auditTrail?.error && <div className="bg-red-50 border border-red-200 text-red-700 p-3 rounded-xl text-sm">{auditTrail.error}</div>}

            {auditTrail?.trail && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="glass-card rounded-xl p-5">
                <p className="text-xs text-gray-400 mb-4">{auditTrail.total_entries} events for <span className="text-gray-800 font-mono font-semibold">{auditTrail.payment_id}</span></p>
                <div className="relative pl-4 border-l-2 border-gray-200 space-y-3">
                  {auditTrail.trail.map((entry: any, i: number) => {
                    const iconMap: Record<string, { icon: any; color: string }> = {
                      failure_detected: { icon: AlertTriangle, color: "text-amber-500" },
                      ai_diagnosis: { icon: Activity, color: "text-blue-500" },
                      policy_decision: { icon: Shield, color: "text-indigo-500" },
                      execution_started: { icon: Play, color: "text-cyan-500" },
                      execution_succeeded: { icon: CheckCircle, color: "text-emerald-500" },
                      execution_failed: { icon: XCircle, color: "text-red-500" },
                      escalated_to_review: { icon: ShieldAlert, color: "text-red-500" },
                      review_approved: { icon: CheckCircle2, color: "text-emerald-500" },
                      review_rejected: { icon: XCircle, color: "text-red-500" },
                      stopping_rule_triggered: { icon: Clock, color: "text-red-500" },
                    };
                    const conf = iconMap[entry.event_type] || { icon: Activity, color: "text-gray-400" };
                    const Icon = conf.icon;
                    return (
                      <div key={i} className="relative">
                        <div className="absolute -left-[21px] top-0.5 w-4 h-4 rounded-full bg-white border-2 border-gray-200 flex items-center justify-center">
                          <Icon className={`w-2.5 h-2.5 ${conf.color}`} />
                        </div>
                        <div className="ml-2">
                          <div className="flex items-baseline gap-2 mb-1">
                            <span className={`text-xs font-semibold ${conf.color}`}>{entry.event_type.replace(/_/g, " ")}</span>
                            <span className="text-[10px] text-gray-400">{entry.created_at ? new Date(entry.created_at).toLocaleString() : ""}</span>
                          </div>
                          <pre className="text-[11px] text-gray-500 font-mono bg-gray-50 p-2 rounded-lg overflow-x-auto whitespace-pre-wrap break-all border border-gray-100">{JSON.stringify(entry.data, null, 2)}</pre>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </motion.div>
            )}

            {!auditTrail && (
              <div className="glass-card rounded-xl py-16 text-center text-gray-400">
                <Eye className="w-10 h-10 mx-auto mb-3 text-gray-300" />
                <p className="text-sm">Enter a payment ID to trace its full recovery journey</p>
                <p className="text-[11px] mt-1 text-gray-400">detection → AI diagnosis → policy → execution → reconciliation</p>
              </div>
            )}
          </motion.div>
        )}

      </div>
    </div>
  );
}
