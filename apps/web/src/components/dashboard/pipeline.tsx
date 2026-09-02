"use client";

import { AnimatePresence, motion } from "framer-motion";
import { LucideIcon, Radar } from "lucide-react";
import clsx from "clsx";

import { EmptyState, Tone, toneChip, toneText } from "@/components/ui";

export type PipelineStage =
  | "idle"
  | "detect"
  | "diagnose"
  | "policy"
  | "execute"
  | "result";

export interface PipelineCard {
  key: string;
  title: string;
  detail: string;
  tone: Tone;
  icon: LucideIcon;
}

const STAGES: { key: PipelineStage; label: string }[] = [
  { key: "detect", label: "Detect" },
  { key: "diagnose", label: "Diagnose" },
  { key: "policy", label: "Policy" },
  { key: "execute", label: "Execute" },
  { key: "result", label: "Result" },
];

const ORDER: PipelineStage[] = [
  "idle",
  "detect",
  "diagnose",
  "policy",
  "execute",
  "result",
];

export function StageRail({ stage }: { stage: PipelineStage }) {
  const currentIndex = ORDER.indexOf(stage);

  return (
    <div className="flex items-center gap-1.5">
      {STAGES.map((s, i) => {
        const stageIndex = ORDER.indexOf(s.key);
        const isDone = currentIndex > stageIndex;
        const isCurrent = currentIndex === stageIndex;

        return (
          <div key={s.key} className="flex flex-1 items-center gap-1.5">
            <div className="flex-1">
              <div className="relative h-1 overflow-hidden rounded-full bg-[rgba(126,160,235,0.12)]">
                <motion.div
                  initial={false}
                  animate={{ width: isDone || isCurrent ? "100%" : "0%" }}
                  transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
                  className={clsx(
                    "h-full rounded-full",
                    isDone
                      ? "bg-[var(--success)]"
                      : "bg-gradient-to-r from-[var(--brand)] to-[var(--brand-bright)]",
                  )}
                />
                {isCurrent && (
                  <span className="scan-bar absolute inset-y-0 left-0 w-1/4 bg-white/40 blur-[2px]" />
                )}
              </div>
              <p
                className={clsx(
                  "mt-1.5 text-[10px] font-medium uppercase tracking-wider transition-colors",
                  isCurrent
                    ? "text-[var(--brand-bright)]"
                    : isDone
                      ? "text-[var(--success)]"
                      : "text-[var(--text-muted)]",
                )}
              >
                {s.label}
              </p>
            </div>
            {i < STAGES.length - 1 && <span className="sr-only">then</span>}
          </div>
        );
      })}
    </div>
  );
}

export function PipelineFeed({
  cards,
  running,
}: {
  cards: PipelineCard[];
  running: boolean;
}) {
  if (!cards.length) {
    return (
      <EmptyState
        icon={Radar}
        title="No active recovery"
        description="Trigger a payment or run a simulation to watch the pipeline execute."
      />
    );
  }

  return (
    <div className="relative">
      <div className="absolute bottom-4 left-[19px] top-4 w-px overflow-hidden bg-[var(--border-default)]">
        {running && (
          <span className="flow-line absolute inset-x-0 h-12 bg-gradient-to-b from-transparent via-[var(--brand-bright)] to-transparent" />
        )}
      </div>

      <ul className="space-y-2.5">
        <AnimatePresence initial={false}>
          {cards.map((card, i) => (
            <motion.li
              key={card.key}
              layout
              initial={{ opacity: 0, x: -12, scale: 0.97 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              exit={{ opacity: 0, scale: 0.97 }}
              transition={{
                type: "spring",
                stiffness: 300,
                damping: 26,
                delay: i === cards.length - 1 ? 0 : 0,
              }}
              className="relative flex gap-3 pl-0"
            >
              <div
                className={clsx(
                  "relative z-10 grid h-10 w-10 shrink-0 place-items-center rounded-xl border backdrop-blur-xl",
                  toneChip(card.tone),
                )}
              >
                <card.icon className="h-4 w-4" strokeWidth={2.2} />
              </div>

              <div className="glass min-w-0 flex-1 rounded-xl px-3.5 py-2.5">
                <p className="text-sm font-semibold tracking-tight text-[var(--text-primary)]">
                  {card.title}
                </p>
                <p className="mt-0.5 break-words text-xs leading-relaxed text-[var(--text-secondary)]">
                  {card.detail}
                </p>
              </div>
            </motion.li>
          ))}
        </AnimatePresence>

        {running && (
          <motion.li
            layout
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="relative flex gap-3"
          >
            <div className="relative z-10 grid h-10 w-10 shrink-0 place-items-center rounded-xl border border-[var(--border-default)] bg-[var(--surface-1)] backdrop-blur-xl">
              <span className="flex gap-0.5">
                {[0, 1, 2].map((d) => (
                  <motion.span
                    key={d}
                    animate={{ opacity: [0.25, 1, 0.25] }}
                    transition={{
                      duration: 1.1,
                      repeat: Infinity,
                      delay: d * 0.18,
                    }}
                    className="h-1 w-1 rounded-full bg-[var(--brand-bright)]"
                  />
                ))}
              </span>
            </div>
            <div className="flex flex-1 items-center">
              <p className="text-xs text-[var(--text-muted)]">Working…</p>
            </div>
          </motion.li>
        )}
      </ul>
    </div>
  );
}

export function ResultBanner({
  result,
}: {
  result: "success" | "escalated" | "blocked" | "error" | null;
}) {
  if (!result) return null;

  const config: Record<
    NonNullable<typeof result>,
    { tone: Tone; label: string; body: string }
  > = {
    success: {
      tone: "success",
      label: "Recovery authorised",
      body: "Policy engine cleared the action and executed securely.",
    },
    escalated: {
      tone: "warning",
      label: "Escalated for human review",
      body: "The policy engine required approval before this action can run.",
    },
    blocked: {
      tone: "danger",
      label: "Blocked by policy",
      body: "A stopping rule prevented execution. Nothing was sent to the gateway.",
    },
    error: {
      tone: "danger",
      label: "Pipeline error",
      body: "The run did not complete. See the event feed for details.",
    },
  };

  const c = config[result];

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className={clsx(
        "mt-4 rounded-xl border px-4 py-3",
        toneChip(c.tone),
      )}
    >
      <p className={clsx("text-sm font-semibold", toneText(c.tone))}>{c.label}</p>
      <p className="mt-0.5 text-xs text-[var(--text-secondary)]">{c.body}</p>
    </motion.div>
  );
}
