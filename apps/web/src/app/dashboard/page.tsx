"use client";

import { useCallback, useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  BarChart3,
  BookOpen,
  Eye,
  Shield,
  ShieldAlert,
  Zap,
} from "lucide-react";

import { api } from "@/lib/api";

import { RequireAuth } from "@/components/require-auth";
import { DashboardShell, TabDef } from "@/components/dashboard/shell";
import { LiveRecoveryTab } from "@/components/dashboard/tab-live";
import { BenchmarkTab } from "@/components/dashboard/tab-benchmark";
import { ReviewsTab } from "@/components/dashboard/tab-reviews";
import { AuditTab } from "@/components/dashboard/tab-audit";
import { SafetyTab } from "@/components/dashboard/tab-safety";
import { TaxonomyTab } from "@/components/dashboard/tab-taxonomy";
import { staggerChildren } from "@/components/ui";

export interface Analytics {
  merchant_id: string;
  total_executions: number;
  successful_recoveries: number;
  failed_recoveries: number;
  recovery_rate_percent: number;
  pending_reviews: number;
  total_audit_entries: number;
  unsafe_action_rate: number;
  approved_recovery_paise: number;
  recent_transactions: Transaction[];
}

export interface Transaction {
  execution_id: string;
  payment_id: string;
  action_type: string;
  status: string;
  message: string;
  external_reference: string | null;
  created_at: string | null;
}

const POLL_INTERVAL_MS = 8000;

export default function DashboardPage() {
  return (
    <RequireAuth>
      <Dashboard />
    </RequireAuth>
  );
}

function Dashboard() {
  const [activeTab, setActiveTab] = useState("live");
  const [analytics, setAnalytics] = useState<Analytics | null>(null);

  const fetchAnalytics = useCallback(async () => {
    try {
      const res = await api.get<Analytics>("/analytics/summary");
      setAnalytics(res.data);
    } catch {
      // 
    }
  }, []);

  useEffect(() => {
    let timer: ReturnType<typeof setInterval> | null = null;

    const start = () => {
      if (timer) return;
      fetchAnalytics();
      timer = setInterval(fetchAnalytics, POLL_INTERVAL_MS);
    };
    const stop = () => {
      if (timer) clearInterval(timer);
      timer = null;
    };

    const onVisibility = () =>
      document.visibilityState === "visible" ? start() : stop();

    start();
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      stop();
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [fetchAnalytics]);

  const tabs: TabDef[] = [
    { key: "live", label: "Live Recovery", icon: Zap },
    { key: "benchmark", label: "50k Benchmark", icon: BarChart3 },
    {
      key: "reviews",
      label: "Escalations",
      icon: Shield,
      badge: analytics?.pending_reviews || undefined,
    },
    { key: "audit", label: "Audit Trail", icon: Eye },
    { key: "safety", label: "Adversarial Wall", icon: ShieldAlert },
    { key: "taxonomy", label: "Taxonomy", icon: BookOpen },
  ];

  return (
    <DashboardShell tabs={tabs} active={activeTab} onTabChange={setActiveTab}>
      <AnimatePresence mode="wait">
        <motion.div
          key={activeTab}
          variants={staggerChildren}
          initial="hidden"
          animate="show"
          exit={{ opacity: 0, y: -8, transition: { duration: 0.15 } }}
          className="space-y-5"
        >
          {activeTab === "live" && (
            <LiveRecoveryTab
              analytics={analytics}
              onChanged={fetchAnalytics}
            />
          )}
          {activeTab === "benchmark" && <BenchmarkTab />}
          {activeTab === "reviews" && <ReviewsTab onChanged={fetchAnalytics} />}
          {activeTab === "audit" && <AuditTab />}
          {activeTab === "safety" && <SafetyTab />}
          {activeTab === "taxonomy" && <TaxonomyTab />}
        </motion.div>
      </AnimatePresence>
    </DashboardShell>
  );
}
