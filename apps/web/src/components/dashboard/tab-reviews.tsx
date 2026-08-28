"use client";

import { useCallback, useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  Check,
  Inbox,
  Lock,
  RefreshCw,
  Shield,
  X,
} from "lucide-react";
import clsx from "clsx";

import { api, errorMessage } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { formatINR, timeAgo, titleCase, truncateId } from "@/lib/format";
import {
  Badge,
  Button,
  EmptyState,
  Mono,
  SectionCard,
  SkeletonRows,
  Tone,
  toneChip,
} from "@/components/ui";

interface Review {
  review_id: string;
  payment_id: string;
  customer_id: string;
  amount: number;
  action_type: string;
  policy_reason: string;
  ai_diagnosis: string;
  ai_confidence: number;
  status: string;
  created_at: string | null;
  resolved_at: string | null;
  resolved_by: string | null;
}

const STATUS_TONE: Record<string, Tone> = {
  pending: "warning",
  approved: "success",
  rejected: "danger",
};

export function ReviewsTab({ onChanged }: { onChanged: () => void }) {
  const { can } = useAuth();
  const canResolve = can("analyst");

  const [reviews, setReviews] = useState<Review[] | null>(null);
  const [filter, setFilter] = useState<"pending" | "all">("pending");
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const res = await api.get<{ reviews: Review[] }>("/reviews/", {
        params: { status: filter },
      });
      setReviews(res.data.reviews);
    } catch (err) {
      setError(errorMessage(err, "Could not load the escalation queue"));
      setReviews([]);
    }
  }, [filter]);

  useEffect(() => {
    setReviews(null);
    load();
  }, [load]);

  const resolve = async (id: string, action: "approve" | "reject") => {
    setBusy(id);
    setError(null);
    try {
      await api.post(`/reviews/${id}/${action}`);
      await load();
      onChanged();
    } catch (err) {
      setError(errorMessage(err, `Could not ${action} this review`));
    } finally {
      setBusy(null);
    }
  };

  return (
    <SectionCard
      title="Escalation queue"
      description="Actions the policy engine refused to execute without a human decision."
      icon={Shield}
      action={
        <div className="flex items-center gap-2">
          <div className="flex rounded-lg border border-[var(--border-default)] bg-[var(--surface-1)] p-0.5">
            {(["pending", "all"] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={clsx(
                  "rounded-md px-2.5 py-1 text-[11px] font-medium capitalize transition",
                  filter === f
                    ? "bg-[var(--brand)] text-white"
                    : "text-[var(--text-muted)] hover:text-[var(--text-secondary)]",
                )}
              >
                {f}
              </button>
            ))}
          </div>
          <Button onClick={load} variant="ghost" icon={RefreshCw}>
            Refresh
          </Button>
        </div>
      }
    >
      {!canResolve && (
        <div className="mb-4 flex items-start gap-2 rounded-xl border border-[var(--border-default)] bg-[var(--surface-1)] px-3 py-2.5">
          <Lock className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[var(--text-muted)]" />
          <p className="text-xs text-[var(--text-muted)]">
            Viewers can read the queue but cannot approve or reject. Approving
            authorises a real charge, so it requires the analyst role.
          </p>
        </div>
      )}

      {error && (
        <div className="mb-4 rounded-xl border border-[rgba(255,90,106,0.32)] bg-[var(--danger-dim)] px-3 py-2.5 text-xs text-[var(--danger)]">
          {error}
        </div>
      )}

      {!reviews ? (
        <SkeletonRows rows={3} />
      ) : reviews.length === 0 ? (
        <EmptyState
          icon={Inbox}
          title={filter === "pending" ? "Queue is clear" : "No reviews yet"}
          description="Escalations appear here when the policy engine requires human approval."
        />
      ) : (
        <ul className="space-y-2.5">
          <AnimatePresence initial={false}>
            {reviews.map((r) => (
              <motion.li
                key={r.review_id}
                layout
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.98 }}
                className="glass rounded-xl p-4"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-mono text-xs text-[var(--text-primary)]">
                        {r.payment_id}
                      </span>
                      <Badge tone={STATUS_TONE[r.status] ?? "neutral"}>
                        {titleCase(r.status)}
                      </Badge>
                      <span className="text-sm font-bold text-[var(--text-primary)]">
                        {formatINR(r.amount)}
                      </span>
                    </div>

                    <p className="mt-2 text-xs leading-relaxed text-[var(--text-secondary)]">
                      <span className="font-medium text-[var(--warning)]">
                        Policy:
                      </span>{" "}
                      {r.policy_reason}
                    </p>

                    {r.ai_diagnosis && (
                      <p className="mt-1.5 text-xs leading-relaxed text-[var(--text-muted)]">
                        <span className="font-medium text-[var(--violet)]">
                          AI:
                        </span>{" "}
                        {r.ai_diagnosis}
                        <span className="ml-1.5 opacity-70">
                          ({Math.round(r.ai_confidence * 100)}% confidence)
                        </span>
                      </p>
                    )}

                    <div className="mt-2.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-[10px] text-[var(--text-muted)]">
                      <span>{titleCase(r.action_type)}</span>
                      <span>·</span>
                      <span>{timeAgo(r.created_at)}</span>
                      {r.resolved_by && (
                        <>
                          <span>·</span>
                          <span>
                            resolved by{" "}
                            <Mono>{truncateId(r.resolved_by, 12)}</Mono>
                          </span>
                        </>
                      )}
                    </div>
                  </div>

                  {r.status === "pending" && canResolve && (
                    <div className="flex gap-2">
                      <Button
                        variant="success"
                        icon={Check}
                        loading={busy === r.review_id}
                        onClick={() => resolve(r.review_id, "approve")}
                      >
                        Approve
                      </Button>
                      <Button
                        variant="danger"
                        icon={X}
                        disabled={busy === r.review_id}
                        onClick={() => resolve(r.review_id, "reject")}
                      >
                        Reject
                      </Button>
                    </div>
                  )}
                </div>
              </motion.li>
            ))}
          </AnimatePresence>
        </ul>
      )}
    </SectionCard>
  );
}
