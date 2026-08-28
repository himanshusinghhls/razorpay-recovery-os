"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Eye, FileSearch, Search } from "lucide-react";

import { api, errorMessage } from "@/lib/api";
import { timeAgo, titleCase, truncateId } from "@/lib/format";
import {
  Badge,
  Button,
  EmptyState,
  Mono,
  SectionCard,
  Tone,
  toneChip,
} from "@/components/ui";

interface TrailEntry {
  event_type: string;
  data: Record<string, unknown>;
  actor: string;
  created_at: string | null;
}

const EVENT_TONE: Record<string, Tone> = {
  failure_detected: "warning",
  ai_diagnosis: "violet",
  policy_decision: "brand",
  execution_started: "brand",
  execution_succeeded: "success",
  execution_failed: "danger",
  escalated_to_review: "warning",
  review_approved: "success",
  review_rejected: "danger",
  webhook_received: "neutral",
  recovery_reconciled: "success",
  stopping_rule_triggered: "danger",
};

export function AuditTab() {
  const [paymentId, setPaymentId] = useState("");
  const [trail, setTrail] = useState<TrailEntry[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const search = async () => {
    const id = paymentId.trim();
    if (!id) return;

    setLoading(true);
    setError(null);
    setTrail(null);
    try {
      const res = await api.get<{ trail: TrailEntry[] }>(`/audit/${id}`);
      setTrail(res.data.trail);
    } catch (err) {
      setError(errorMessage(err, "No audit trail found for that payment"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <SectionCard
      title="Audit trail"
      description="Complete, ordered provenance for any payment your merchant has processed."
      icon={Eye}
    >
      <div className="flex flex-wrap gap-2">
        <div className="relative min-w-0 flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--text-muted)]" />
          <input
            value={paymentId}
            onChange={(e) => setPaymentId(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && search()}
            placeholder="pay_XXXXXXXXXXXX"
            className="w-full rounded-xl border border-[var(--border-default)] bg-[var(--surface-1)] py-2.5 pl-10 pr-3 font-mono text-sm outline-none transition placeholder:font-sans placeholder:text-[var(--text-muted)] focus:border-[var(--brand)]"
          />
        </div>
        <Button onClick={search} loading={loading} icon={FileSearch}>
          Trace
        </Button>
      </div>

      {error && (
        <div className="mt-4 rounded-xl border border-[rgba(255,90,106,0.32)] bg-[var(--danger-dim)] px-3 py-2.5 text-xs text-[var(--danger)]">
          {error}
        </div>
      )}

      {!trail && !error && !loading && (
        <div className="mt-2">
          <EmptyState
            icon={FileSearch}
            title="Trace a payment"
            description="Enter a payment id to replay every step the system took."
          />
        </div>
      )}

      {trail && (
        <div className="relative mt-5">
          <div className="absolute bottom-2 left-[7px] top-2 w-px bg-[var(--border-default)]" />
          <ol className="space-y-3">
            {trail.map((e, i) => {
              const tone = EVENT_TONE[e.event_type] ?? "neutral";
              return (
                <motion.li
                  key={i}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="relative flex gap-3.5"
                >
                  <span
                    className={`relative z-10 mt-1 h-[15px] w-[15px] shrink-0 rounded-full border-2 ${toneChip(tone)}`}
                  />
                  <div className="min-w-0 flex-1 pb-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge tone={tone}>{titleCase(e.event_type)}</Badge>
                      <span className="text-[10px] text-[var(--text-muted)]">
                        {timeAgo(e.created_at)} · <Mono>{truncateId(e.actor, 14)}</Mono>
                      </span>
                    </div>
                    {Object.keys(e.data ?? {}).length > 0 && (
                      <pre className="mt-1.5 max-w-full overflow-x-auto rounded-lg border border-[var(--border-subtle)] bg-[rgba(5,8,15,0.5)] p-2.5 font-mono text-[10px] leading-relaxed text-[var(--text-secondary)]">
                        {JSON.stringify(e.data, null, 2)}
                      </pre>
                    )}
                  </div>
                </motion.li>
              );
            })}
          </ol>
        </div>
      )}
    </SectionCard>
  );
}
