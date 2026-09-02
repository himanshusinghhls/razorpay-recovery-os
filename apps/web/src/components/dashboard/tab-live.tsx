"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  Activity,
  AlertTriangle,
  Ban,
  CheckCircle2,
  ChevronDown,
  Clock,
  CreditCard,
  Cpu,
  Database,
  IndianRupee,
  Link as LinkIcon,
  Lock,
  Package,
  Play,
  Radar,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  StopCircle,
  TrendingUp,
  User,
  WalletCards,
  XCircle,
} from "lucide-react";
import clsx from "clsx";

import { api, errorMessage } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import {
  formatINR,
  formatINRCompact,
  timeAgo,
  titleCase,
  truncateId,
} from "@/lib/format";
import {
  Badge,
  Button,
  EmptyState,
  MetricTile,
  Mono,
  SectionCard,
  SkeletonRows,
  Tone,
  fadeUp,
  toneChip,
  toneText,
} from "@/components/ui";
import {
  PipelineCard,
  PipelineFeed,
  PipelineStage,
  ResultBanner,
  StageRail,
} from "@/components/dashboard/pipeline";
import type { Analytics, Transaction } from "@/app/dashboard/page";

const FAILURE_REASONS = [
  { value: "insufficient_funds", label: "Insufficient Funds", icon: WalletCards },
  { value: "temporary_network_timeout", label: "Network Timeout", icon: Activity },
  { value: "suspected_fraud", label: "Suspected Fraud", icon: ShieldAlert },
  { value: "card_expired", label: "Card Expired", icon: Clock },
];

const QUICK_AMOUNTS = [499, 2499, 14999, 89999];

// Bounds on the status poll. The previous implementation looped forever, so a
// job that died left the browser polling for the rest of the session.
const POLL_INTERVAL_MS = 1500;
const POLL_TIMEOUT_MS = 90_000;

/** Short pause so consecutive stage changes render as distinct steps. */
const beat = (ms = 420) => new Promise((r) => setTimeout(r, ms));

const STATUS_TONE: Record<string, Tone> = {
  succeeded: "success",
  started: "brand",
  failed: "danger",
  created: "neutral",
  unknown: "neutral",
};

interface RecoveryResult {
  execution_id: string;
  status: string;
  action_type: string;
  provider_reference: string | null;
  message: string;
  pipeline_latency_ms?: number;
}

export function LiveRecoveryTab({
  analytics,
  onChanged,
}: {
  analytics: Analytics | null;
  onChanged: () => void;
}) {
  const { can } = useAuth();
  const canRun = can("analyst");

  const [amountInput, setAmountInput] = useState("499");
  const [failureReason, setFailureReason] = useState("insufficient_funds");
  const [simulateMode, setSimulateMode] = useState(true);

  const [stage, setStage] = useState<PipelineStage>("idle");
  const [result, setResult] = useState<
    "success" | "escalated" | "blocked" | "error" | null
  >(null);
  const [cards, setCards] = useState<PipelineCard[]>([]);
  const [running, setRunning] = useState(false);

  const amount = Math.max(0, parseInt(amountInput, 10) || 0);
  const cancelled = useRef(false);

  // Must be reset on mount, not only set on unmount: React StrictMode runs
  // effects mount → unmount → mount in development, so a cleanup-only version
  // latches this to true on the throwaway first pass and every later poll
  // aborts immediately with "cancelled".
  useEffect(() => {
    cancelled.current = false;
    return () => {
      cancelled.current = true;
    };
  }, []);

  const push = useCallback(
    (key: string, title: string, detail: string, tone: Tone, icon: typeof Cpu) => {
      setCards((prev) => [...prev, { key: `${key}-${prev.length}`, title, detail, tone, icon }]);
    },
    [],
  );

  const reset = () => {
    setCards([]);
    setResult(null);
    setStage("detect");
    setRunning(true);
  };

  /** Poll a queued job until it leaves the processing state, or we give up. */
  const pollUntilDone = useCallback(
    async (jobId: string): Promise<RecoveryResult> => {
      const deadline = Date.now() + POLL_TIMEOUT_MS;

      while (Date.now() < deadline) {
        if (cancelled.current) throw new Error("cancelled");
        await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS));

        try {
          const res = await api.get<RecoveryResult>(
            `/recoveries/status/${jobId}`,
          );
          if (res.data?.status && res.data.status !== "processing") {
            return res.data;
          }
        } catch (err) {
          // A 404 means the job record expired or never landed; anything else
          // is worth one more attempt before the deadline.
          if (
            typeof err === "object" &&
            err !== null &&
            "response" in err &&
            (err as { response?: { status?: number } }).response?.status === 404
          ) {
            throw new Error("Job not found — the worker may not be running");
          }
        }
      }

      throw new Error("Timed out waiting for the recovery worker");
    },
    [],
  );

  /**
   * Walk the rail through the stages the run actually passed.
   *
   * Deliberately paced: setting several stages in one synchronous pass gets
   * batched by React, so the rail would snap from "diagnose" to "result" and
   * the policy/execute steps would never be seen.
   */
  const renderOutcome = useCallback(
    async (data: RecoveryResult) => {
      setStage("policy");
      await beat();

      if (data.status === "escalated") {
        push("policy", "Policy: human approval required", data.message, "warning", ShieldAlert);
        await beat();
        setStage("result");
        setResult("escalated");
        push(
          "escalated",
          "Escalated to review queue",
          `Review ${truncateId(data.provider_reference, 20)}`,
          "warning",
          User,
        );
        return;
      }

      if (data.status === "failed") {
        push("policy", "Policy: blocked", data.message, "danger", StopCircle);
        await beat();
        setStage("result");
        setResult("blocked");
        push(
          "stopped",
          "Recovery stopped",
          "A stopping rule or policy violation prevented execution.",
          "danger",
          Ban,
        );
        return;
      }

      push("policy", "Policy: approved", "All safety checks passed.", "success", ShieldCheck);
      await beat();
      setStage("execute");
      push(
        "execute",
        "Executed via Payment Gateway",
        data.provider_reference
          ? `Order ${data.provider_reference}`
          : truncateId(data.execution_id, 20),
        "brand",
        LinkIcon,
      );
      await beat();
      setStage("result");
      setResult("success");
      push(
        "done",
        "Recovery initiated",
        `${titleCase(data.action_type)}${
          data.pipeline_latency_ms
            ? ` · ${Math.round(data.pipeline_latency_ms)}ms end to end`
            : ""
        }`,
        "success",
        Sparkles,
      );
    },
    [push],
  );

  const runRecovery = useCallback(
    async (paymentId: string, reason: string, amountPaise: number) => {
      setStage("diagnose");
      push(
        "diagnose",
        "AI analyst engaged",
        "AI Analysis Core is diagnosing the failure and estimating recovery probability…",
        "violet",
        Cpu,
      );

      try {
        const res = await api.post<{ execution_id: string }>(
          "/recoveries/execute",
          {
            payment_id: paymentId,
            customer_id: "cust_demo_001",
            amount: amountPaise,
            failure_reason: reason,
          },
          { headers: { "Idempotency-Key": crypto.randomUUID() } },
        );

        const data = await pollUntilDone(res.data.execution_id);
        await renderOutcome(data);
        onChanged();
      } catch (err) {
        if ((err as Error)?.message === "cancelled") return;
        setStage("result");
        setResult("error");
        push("error", "Pipeline error", errorMessage(err), "danger", XCircle);
      } finally {
        setRunning(false);
      }
    },
    [push, pollUntilDone, renderOutcome, onChanged],
  );

  const handleSimulate = async () => {
    if (!amount) return;
    reset();
    const paymentId = `pay_sim_${Math.random().toString(36).slice(2, 10)}`;
    push(
      "detect",
      "Failure detected",
      `${formatINR(amount * 100)} · ${paymentId}`,
      "warning",
      AlertTriangle,
    );
    await runRecovery(paymentId, failureReason, amount * 100);
  };

  const handleRealPayment = async () => {
    if (!amount) return;
    reset();
    const amountPaise = amount * 100;

    push(
      "init",
      "Payment initiated",
      `${formatINR(amountPaise)} via Secure Checkout`,
      "brand",
      CreditCard,
    );

    let handled = false;

    try {
      const orderRes = await api.post<{
        order_id: string;
        amount: number;
        key_id: string;
      }>(`/recoveries/create-order?amount=${amountPaise}`);

      const { order_id, amount: orderAmount, key_id } = orderRes.data;
      push("order", "Order created", `Razorpay order ${order_id}`, "brand", Package);

      const RazorpayCtor = (
        window as unknown as { Razorpay?: new (o: unknown) => { open: () => void; on: (e: string, cb: (r: never) => void) => void } }
      ).Razorpay;

      if (!RazorpayCtor) {
        throw new Error("Razorpay Checkout failed to load");
      }

      const rzp = new RazorpayCtor({
        key: key_id,
        amount: orderAmount,
        currency: "INR",
        name: "RecoveryOS",
        description: "AI-powered revenue recovery",
        order_id,
        theme: { color: "#2b6aff" },
        handler: async (response: { razorpay_payment_id: string }) => {
          if (handled) return;
          handled = true;
          setStage("result");
          setResult("success");
          push(
            "paid",
            "Payment succeeded",
            `Payment ${response.razorpay_payment_id} — no recovery needed.`,
            "success",
            CheckCircle2,
          );
          setRunning(false);
          try {
            await api.post("/audit/log-success", {
              payment_id: response.razorpay_payment_id,
              amount: amountPaise,
            });
          } catch {
            // Logging the happy path is best effort.
          }
          onChanged();
        },
        modal: {
          ondismiss: () => {
            if (handled) return;
            handled = true;
            setStage("detect");
            push(
              "abandoned",
              "Checkout abandoned",
              "Customer closed the payment window — triggering AI recovery.",
              "warning",
              AlertTriangle,
            );
            void runRecovery(
              `pay_ab_${Math.random().toString(36).slice(2, 10)}`,
              "checkout_abandoned",
              amountPaise,
            );
          },
        },
      });

      rzp.on("payment.failed", (resp: { error?: { description?: string; metadata?: { payment_id?: string } } }) => {
        if (handled) return;
        handled = true;
        const reason = resp?.error?.description || "unknown_error";
        setStage("detect");
        push("failed", "Payment failed", `Reason: ${reason}`, "danger", XCircle);
        void runRecovery(
          resp?.error?.metadata?.payment_id ||
            `pay_f_${Math.random().toString(36).slice(2, 10)}`,
          "insufficient_funds",
          amountPaise,
        );
      });

      rzp.open();
    } catch (err) {
      setStage("result");
      setResult("error");
      push("error", "Could not start checkout", errorMessage(err), "danger", XCircle);
      setRunning(false);
    }
  };

  return (
    <>
      <motion.div
        variants={fadeUp}
        className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6"
      >
        <MetricTile
          label="Total runs"
          value={analytics?.total_executions ?? 0}
          icon={Activity}
          tone="brand"
          loading={!analytics}
        />
        <MetricTile
          label="Recovered"
          value={analytics?.successful_recoveries ?? 0}
          icon={CheckCircle2}
          tone="success"
          loading={!analytics}
        />
        <MetricTile
          label="Recovery rate"
          value={analytics ? `${analytics.recovery_rate_percent}%` : "—"}
          icon={TrendingUp}
          tone="success"
          loading={!analytics}
        />
        <MetricTile
          label="Approved value"
          value={
            analytics ? formatINRCompact(analytics.approved_recovery_paise) : "—"
          }
          icon={IndianRupee}
          tone="violet"
          loading={!analytics}
        />
        <MetricTile
          label="Escalations"
          value={analytics?.pending_reviews ?? 0}
          icon={Shield}
          tone="warning"
          loading={!analytics}
        />
        <MetricTile
          label="Audit entries"
          value={analytics?.total_audit_entries ?? 0}
          icon={Database}
          tone="neutral"
          loading={!analytics}
        />
      </motion.div>

      <div className="grid gap-5 lg:grid-cols-[minmax(0,340px)_minmax(0,1fr)]">
        <SectionCard
          title="Trigger a recovery"
          description="Simulate a failure, or run a real secure checkout."
          icon={Play}
        >
          {!canRun && (
            <div className="mb-4 flex items-start gap-2 rounded-xl border border-[var(--border-default)] bg-[var(--surface-1)] px-3 py-2.5">
              <Lock className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[var(--text-muted)]" />
              <p className="text-xs text-[var(--text-muted)]">
                Your <strong>viewer</strong> role is read-only. An analyst or
                admin can trigger recoveries.
              </p>
            </div>
          )}

          <label className="mb-1.5 block text-xs font-medium text-[var(--text-secondary)]">
            Amount
          </label>
          <div className="relative">
            <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-sm text-[var(--text-muted)]">
              ₹
            </span>
            <input
              type="number"
              min={1}
              value={amountInput}
              onChange={(e) => setAmountInput(e.target.value)}
              disabled={!canRun || running}
              className="w-full rounded-xl border border-[var(--border-default)] bg-[var(--surface-1)] py-2.5 pl-7 pr-3 text-sm outline-none transition focus:border-[var(--brand)] disabled:opacity-50"
            />
          </div>

          <div className="mt-2 flex flex-wrap gap-1.5">
            {QUICK_AMOUNTS.map((a) => (
              <button
                key={a}
                onClick={() => setAmountInput(String(a))}
                disabled={!canRun || running}
                className={clsx(
                  "rounded-lg border px-2 py-1 text-[11px] font-medium transition disabled:opacity-40",
                  amount === a
                    ? "border-[var(--brand)] bg-[rgba(43,106,255,0.16)] text-[var(--brand-bright)]"
                    : "border-[var(--border-default)] text-[var(--text-muted)] hover:text-[var(--text-secondary)]",
                )}
              >
                ₹{a.toLocaleString("en-IN")}
              </button>
            ))}
          </div>

          <div className="mt-4 flex rounded-xl border border-[var(--border-default)] bg-[var(--surface-1)] p-1">
            {[
              { key: true, label: "Simulate failure" },
              { key: false, label: "Real checkout" },
            ].map((m) => (
              <button
                key={String(m.key)}
                onClick={() => setSimulateMode(m.key)}
                disabled={!canRun || running}
                className={clsx(
                  "relative flex-1 rounded-lg px-2 py-1.5 text-xs font-medium transition-colors disabled:opacity-50",
                  simulateMode === m.key
                    ? "text-white"
                    : "text-[var(--text-muted)] hover:text-[var(--text-secondary)]",
                )}
              >
                {simulateMode === m.key && (
                  <motion.span
                    layoutId="mode-pill"
                    className="absolute inset-0 rounded-lg bg-gradient-to-b from-[var(--brand-bright)] to-[var(--brand)]"
                    transition={{ type: "spring", stiffness: 320, damping: 30 }}
                  />
                )}
                <span className="relative">{m.label}</span>
              </button>
            ))}
          </div>

          <AnimatePresence initial={false}>
            {simulateMode && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                className="overflow-hidden"
              >
                <label className="mb-1.5 mt-4 block text-xs font-medium text-[var(--text-secondary)]">
                  Failure reason
                </label>
                <div className="grid grid-cols-2 gap-1.5">
                  {FAILURE_REASONS.map((r) => (
                    <button
                      key={r.value}
                      onClick={() => setFailureReason(r.value)}
                      disabled={!canRun || running}
                      className={clsx(
                        "flex items-center gap-1.5 rounded-lg border px-2 py-2 text-left text-[11px] font-medium transition disabled:opacity-40",
                        failureReason === r.value
                          ? "border-[var(--brand)] bg-[rgba(43,106,255,0.14)] text-[var(--brand-bright)]"
                          : "border-[var(--border-default)] text-[var(--text-muted)] hover:text-[var(--text-secondary)]",
                      )}
                    >
                      <r.icon className="h-3.5 w-3.5 shrink-0" />
                      <span className="truncate">{r.label}</span>
                    </button>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          <Button
            onClick={simulateMode ? handleSimulate : handleRealPayment}
            disabled={!canRun || !amount}
            loading={running}
            icon={simulateMode ? Play : CreditCard}
            className="mt-5 w-full"
          >
            {running
              ? "Running pipeline…"
              : simulateMode
                ? "Run simulation"
                : "Open checkout"}
          </Button>
        </SectionCard>

        <SectionCard
          title="Recovery pipeline"
          description="Detection → AI diagnosis → policy → execution."
          icon={Radar}
          action={
            stage !== "idle" && (
              <Badge tone={running ? "brand" : "neutral"} pulse={running}>
                {running ? "Running" : "Complete"}
              </Badge>
            )
          }
        >
          <div className="mb-5">
            <StageRail stage={stage} />
          </div>
          <PipelineFeed cards={cards} running={running} />
          <ResultBanner result={result} />
        </SectionCard>
      </div>

      <RecentTransactions transactions={analytics?.recent_transactions} />
    </>
  );
}

function RecentTransactions({
  transactions,
}: {
  transactions?: Transaction[];
}) {
  const [expanded, setExpanded] = useState<string | null>(null);
  const [trails, setTrails] = useState<Record<string, TrailState>>({});

  interface TrailState {
    loading?: boolean;
    error?: string;
    entries?: {
      event_type: string;
      data: Record<string, unknown>;
      actor: string;
      created_at: string | null;
    }[];
  }

  const toggle = async (paymentId: string) => {
    if (expanded === paymentId) {
      setExpanded(null);
      return;
    }
    setExpanded(paymentId);

    if (trails[paymentId]) return;
    setTrails((p) => ({ ...p, [paymentId]: { loading: true } }));
    try {
      const res = await api.get(`/audit/${paymentId}`);
      setTrails((p) => ({ ...p, [paymentId]: { entries: res.data.trail } }));
    } catch (err) {
      setTrails((p) => ({
        ...p,
        [paymentId]: { error: errorMessage(err, "No audit trail found") },
      }));
    }
  };

  return (
    <SectionCard
      title="Recent activity"
      description="Every execution for your merchant, newest first."
      icon={Activity}
    >
      {!transactions ? (
        <SkeletonRows rows={4} />
      ) : transactions.length === 0 ? (
        <EmptyState
          icon={Database}
          title="No executions yet"
          description="Run a recovery to populate the ledger."
        />
      ) : (
        <ul className="space-y-2">
          {transactions.map((t) => {
            const tone = STATUS_TONE[t.status] ?? "neutral";
            const isOpen = expanded === t.payment_id;
            const trail = trails[t.payment_id];

            return (
              <li key={t.execution_id} className="glass rounded-xl">
                <button
                  onClick={() => toggle(t.payment_id)}
                  className="flex w-full items-center gap-3 px-3.5 py-3 text-left"
                >
                  <span
                    className={clsx(
                      "grid h-8 w-8 shrink-0 place-items-center rounded-lg border",
                      toneChip(tone),
                    )}
                  >
                    {t.status === "failed" ? (
                      <XCircle className="h-4 w-4" />
                    ) : t.status === "succeeded" ? (
                      <CheckCircle2 className="h-4 w-4" />
                    ) : (
                      <Activity className="h-4 w-4" />
                    )}
                  </span>

                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-mono text-xs text-[var(--text-primary)]">
                        {t.payment_id}
                      </span>
                      <Badge tone={tone}>{titleCase(t.status)}</Badge>
                      <span className="text-[11px] text-[var(--text-muted)]">
                        {titleCase(t.action_type)}
                      </span>
                    </div>
                    <p className="mt-0.5 truncate text-[11px] text-[var(--text-muted)]">
                      {t.message}
                    </p>
                  </div>

                  <span className="shrink-0 text-[11px] text-[var(--text-muted)]">
                    {timeAgo(t.created_at)}
                  </span>
                  <ChevronDown
                    className={clsx(
                      "h-4 w-4 shrink-0 text-[var(--text-muted)] transition-transform",
                      isOpen && "rotate-180",
                    )}
                  />
                </button>

                <AnimatePresence initial={false}>
                  {isOpen && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.22 }}
                      className="overflow-hidden border-t border-[var(--border-subtle)]"
                    >
                      <div className="px-3.5 py-3">
                        {trail?.loading && (
                          <p className="text-xs text-[var(--text-muted)]">
                            Loading audit trail…
                          </p>
                        )}
                        {trail?.error && (
                          <p className="text-xs text-[var(--text-muted)]">
                            {trail.error}
                          </p>
                        )}
                        {trail?.entries && (
                          <ol className="space-y-2">
                            {trail.entries.map((e, i) => (
                              <li key={i} className="flex gap-2.5 text-xs">
                                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--brand)]" />
                                <div className="min-w-0">
                                  <span className="font-medium text-[var(--text-secondary)]">
                                    {titleCase(e.event_type)}
                                  </span>
                                  <span className="ml-2 text-[10px] text-[var(--text-muted)]">
                                    {timeAgo(e.created_at)} · by{" "}
                                    <Mono>{truncateId(e.actor, 12)}</Mono>
                                  </span>
                                </div>
                              </li>
                            ))}
                          </ol>
                        )}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </li>
            );
          })}
        </ul>
      )}
    </SectionCard>
  );
}
