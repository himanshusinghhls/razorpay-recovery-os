"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import {
  BarChart3,
  Ban,
  Gauge,
  Play,
  ShieldAlert,
  TrendingUp,
  Users,
} from "lucide-react";

import { api, errorMessage, SLOW_REQUEST } from "@/lib/api";
import { formatINRCompact, formatNumber } from "@/lib/format";
import {
  Badge,
  Button,
  EmptyState,
  MetricTile,
  SectionCard,
  fadeUp,
} from "@/components/ui";

interface BenchmarkResult {
  total_events: number;
  baseline_recovery_paise: number;
  ai_recovery_paise: number;
  incremental_uplift_percent: number;
  policy_blocks: number;
  escalations: number;
  unsafe_action_rate: number;
}

export function BenchmarkTab() {
  const [data, setData] = useState<BenchmarkResult | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    setRunning(true);
    setError(null);
    try {
      const res = await api.post<BenchmarkResult>(
        "/analytics/simulate-benchmark",
        undefined,
        SLOW_REQUEST,
      );
      setData(res.data);
    } catch (err) {
      setError(errorMessage(err, "Benchmark failed"));
    } finally {
      setRunning(false);
    }
  };

  const max = data
    ? Math.max(data.baseline_recovery_paise, data.ai_recovery_paise)
    : 1;

  return (
    <SectionCard
      title="50,000 event benchmark"
      description="Synthetic failure batch evaluated against the deterministic policy engine."
      icon={BarChart3}
      action={
        <Button onClick={run} loading={running} icon={Play} variant="ghost">
          {running ? "Running…" : data ? "Re-run" : "Run benchmark"}
        </Button>
      }
    >
      {error && (
        <div className="mb-4 rounded-xl border border-[rgba(255,90,106,0.32)] bg-[var(--danger-dim)] px-3 py-2.5 text-xs text-[var(--danger)]">
          {error}
        </div>
      )}

      {!data && !running && (
        <EmptyState
          icon={Gauge}
          title="No benchmark run yet"
          description="Evaluates 50,000 synthetic payment failures through the full policy engine."
        />
      )}

      {running && !data && (
        <div className="space-y-3 py-8 text-center">
          <div className="mx-auto h-1.5 w-56 overflow-hidden rounded-full bg-[rgba(126,160,235,0.14)]">
            <span className="scan-bar block h-full w-1/3 rounded-full bg-gradient-to-r from-[var(--brand)] to-[var(--brand-bright)]" />
          </div>
          <p className="text-xs text-[var(--text-muted)]">
            Evaluating 50,000 events through the policy engine…
          </p>
        </div>
      )}

      {data && (
        <div className="space-y-5">
          <motion.div
            variants={fadeUp}
            initial="hidden"
            animate="show"
            className="grid grid-cols-2 gap-3 lg:grid-cols-4"
          >
            <MetricTile
              label="Events"
              value={data.total_events}
              icon={Users}
              tone="neutral"
            />
            <MetricTile
              label="Uplift"
              value={`+${data.incremental_uplift_percent}%`}
              icon={TrendingUp}
              tone="success"
            />
            <MetricTile
              label="Policy blocks"
              value={data.policy_blocks}
              icon={Ban}
              tone="danger"
            />
            <MetricTile
              label="Escalations"
              value={data.escalations}
              icon={ShieldAlert}
              tone="warning"
            />
          </motion.div>

          <div className="glass rounded-xl p-5">
            <p className="mb-4 text-xs font-medium uppercase tracking-wider text-[var(--text-muted)]">
              Recovered value
            </p>

            <Bar
              label="Baseline (static retry rules)"
              value={data.baseline_recovery_paise}
              max={max}
              tone="neutral"
            />
            <Bar
              label="RecoveryOS (AI + policy engine)"
              value={data.ai_recovery_paise}
              max={max}
              tone="brand"
              delay={0.15}
            />
          </div>

          <div className="flex flex-wrap items-center gap-2 rounded-xl border border-[rgba(16,217,160,0.28)] bg-[var(--success-dim)] px-4 py-3">
            <Badge tone="success">
              {data.unsafe_action_rate}% unsafe actions — all blocked
            </Badge>
            <p className="text-xs text-[var(--text-secondary)]">
              The AI proposed {formatNumber(data.policy_blocks)} actions the
              policy engine refused. None reached the gateway.
            </p>
          </div>
        </div>
      )}
    </SectionCard>
  );
}

function Bar({
  label,
  value,
  max,
  tone,
  delay = 0,
}: {
  label: string;
  value: number;
  max: number;
  tone: "neutral" | "brand";
  delay?: number;
}) {
  const pct = max > 0 ? (value / max) * 100 : 0;

  return (
    <div className="mb-4 last:mb-0">
      <div className="mb-1.5 flex items-baseline justify-between">
        <span className="text-xs text-[var(--text-secondary)]">{label}</span>
        <span
          className={
            tone === "brand"
              ? "text-sm font-bold text-[var(--brand-bright)]"
              : "text-sm font-semibold text-[var(--text-muted)]"
          }
        >
          {formatINRCompact(value)}
        </span>
      </div>
      <div className="h-2.5 overflow-hidden rounded-full bg-[rgba(126,160,235,0.10)]">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.9, delay, ease: [0.22, 1, 0.36, 1] }}
          className={
            tone === "brand"
              ? "h-full rounded-full bg-gradient-to-r from-[var(--brand)] via-[var(--brand-bright)] to-[var(--violet)] shadow-[0_0_16px_-2px_var(--brand-glow)]"
              : "h-full rounded-full bg-[rgba(126,160,235,0.35)]"
          }
        />
      </div>
    </div>
  );
}
