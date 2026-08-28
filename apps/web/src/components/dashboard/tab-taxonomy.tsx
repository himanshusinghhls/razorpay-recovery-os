"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { BookOpen, MessageSquareOff, MessagesSquare, Repeat } from "lucide-react";
import clsx from "clsx";

import { api, errorMessage } from "@/lib/api";
import { titleCase } from "@/lib/format";
import {
  Badge,
  Mono,
  SectionCard,
  SkeletonRows,
  Tone,
  fadeUp,
} from "@/components/ui";

interface TaxonomyClass {
  category: string;
  recovery_class: string;
  default_action: string;
  allow_contact: boolean;
  max_retries: number;
  reason_code: string;
  ai_recovery_probability: number;
  simulation_weight: number;
  notes?: string;
}

interface Taxonomy {
  version?: string;
  classes?: Record<string, TaxonomyClass>;
  error?: string;
}

const CLASS_TONE: Record<string, Tone> = {
  RETRY_FIXABLE: "success",
  CUSTOMER_ACTION: "warning",
  NON_RECOVERABLE: "danger",
  FRAUD_STOP: "danger",
};

export function TaxonomyTab() {
  const [data, setData] = useState<Taxonomy | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const res = await api.get<Taxonomy>("/analytics/taxonomy");
        setData(res.data);
      } catch (err) {
        setError(errorMessage(err, "Could not load the taxonomy"));
      }
    })();
  }, []);

  const classes = Object.entries(data?.classes ?? {});

  return (
    <SectionCard
      title="Failure taxonomy"
      description="The declarative rulebook the agent and policy engine both read from."
      icon={BookOpen}
      action={
        data?.version && <Badge tone="neutral">v{data.version}</Badge>
      }
    >
      {error && (
        <div className="rounded-xl border border-[rgba(255,90,106,0.32)] bg-[var(--danger-dim)] px-3 py-2.5 text-xs text-[var(--danger)]">
          {error}
        </div>
      )}

      {!data && !error && <SkeletonRows rows={5} />}

      {classes.length > 0 && (
        <div className="grid gap-3 md:grid-cols-2">
          {classes.map(([name, cfg], i) => {
            const tone = CLASS_TONE[cfg.recovery_class] ?? "neutral";
            const prob = Math.round((cfg.ai_recovery_probability ?? 0) * 100);

            return (
              <motion.div
                key={name}
                variants={fadeUp}
                initial="hidden"
                animate="show"
                transition={{ delay: i * 0.04 }}
                className="glass rounded-xl p-4"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-mono text-xs font-semibold text-[var(--text-primary)]">
                    {name}
                  </span>
                  <Badge tone={tone}>{titleCase(cfg.recovery_class)}</Badge>
                </div>

                <div className="mt-3">
                  <div className="mb-1 flex items-baseline justify-between">
                    <span className="text-[10px] uppercase tracking-wider text-[var(--text-muted)]">
                      Recovery probability
                    </span>
                    <span className="text-xs font-bold text-[var(--brand-bright)]">
                      {prob}%
                    </span>
                  </div>
                  <div className="h-1.5 overflow-hidden rounded-full bg-[rgba(126,160,235,0.10)]">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${prob}%` }}
                      transition={{
                        duration: 0.7,
                        delay: 0.1 + i * 0.04,
                        ease: [0.22, 1, 0.36, 1],
                      }}
                      className="h-full rounded-full bg-gradient-to-r from-[var(--brand)] to-[var(--brand-bright)]"
                    />
                  </div>
                </div>

                <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1.5 text-[10px] text-[var(--text-muted)]">
                  <span className="inline-flex items-center gap-1">
                    <Repeat className="h-3 w-3" />
                    max {cfg.max_retries} retries
                  </span>
                  <span
                    className={clsx(
                      "inline-flex items-center gap-1",
                      cfg.allow_contact
                        ? "text-[var(--warning)]"
                        : "text-[var(--text-muted)]",
                    )}
                  >
                    {cfg.allow_contact ? (
                      <MessagesSquare className="h-3 w-3" />
                    ) : (
                      <MessageSquareOff className="h-3 w-3" />
                    )}
                    {cfg.allow_contact ? "contact allowed" : "no contact"}
                  </span>
                  <Mono>{cfg.default_action}</Mono>
                </div>

                {cfg.notes && (
                  <p className="mt-2.5 border-t border-[var(--border-subtle)] pt-2.5 text-[11px] leading-relaxed text-[var(--text-secondary)]">
                    {cfg.notes}
                  </p>
                )}
              </motion.div>
            );
          })}
        </div>
      )}
    </SectionCard>
  );
}
