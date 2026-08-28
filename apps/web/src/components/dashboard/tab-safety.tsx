"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import {
  CheckCircle2,
  Cpu,
  Play,
  ShieldAlert,
  ShieldCheck,
  Swords,
  XCircle,
} from "lucide-react";
import clsx from "clsx";

import { api, errorMessage, SLOW_REQUEST } from "@/lib/api";
import { titleCase } from "@/lib/format";
import {
  Badge,
  Button,
  EmptyState,
  SectionCard,
  fadeUp,
} from "@/components/ui";

interface AdversarialResult {
  name: string;
  attack_type: string;
  ai_status: string;
  ai_response: string;
  policy_status: string;
  policy_response: string;
}

export function SafetyTab() {
  const [results, setResults] = useState<AdversarialResult[] | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    setRunning(true);
    setError(null);
    try {
      const res = await api.get<{ results: AdversarialResult[] }>(
        "/safety/adversarial",
        SLOW_REQUEST,
      );
      setResults(res.data.results);
    } catch (err) {
      setError(errorMessage(err, "Could not run the adversarial suite"));
    } finally {
      setRunning(false);
    }
  };

  const held =
    results?.every((r) => r.policy_status === "passed") ?? false;

  return (
    <SectionCard
      title="Adversarial wall"
      description="Prompt injection, amount manipulation and fraud probes fired at the live pipeline."
      icon={ShieldAlert}
      action={
        <Button onClick={run} loading={running} icon={Play} variant="ghost">
          {running ? "Attacking…" : results ? "Re-run" : "Run suite"}
        </Button>
      }
    >
      {error && (
        <div className="mb-4 rounded-xl border border-[rgba(255,90,106,0.32)] bg-[var(--danger-dim)] px-3 py-2.5 text-xs text-[var(--danger)]">
          {error}
        </div>
      )}

      {!results && !running && (
        <EmptyState
          icon={Swords}
          title="Suite not run"
          description="Fires adversarial inputs at the AI and verifies the policy engine still holds the line."
        />
      )}

      {running && !results && (
        <div className="space-y-3 py-8 text-center">
          <div className="mx-auto h-1.5 w-56 overflow-hidden rounded-full bg-[rgba(126,160,235,0.14)]">
            <span className="scan-bar block h-full w-1/3 rounded-full bg-gradient-to-r from-[var(--danger)] to-[var(--warning)]" />
          </div>
          <p className="text-xs text-[var(--text-muted)]">
            Running live attacks against the agent and policy engine…
          </p>
        </div>
      )}

      {results && (
        <div className="space-y-4">
          <div
            className={clsx(
              "flex items-center gap-2.5 rounded-xl border px-4 py-3",
              held
                ? "border-[rgba(16,217,160,0.3)] bg-[var(--success-dim)]"
                : "border-[rgba(255,90,106,0.3)] bg-[var(--danger-dim)]",
            )}
          >
            {held ? (
              <ShieldCheck className="h-5 w-5 shrink-0 text-[var(--success)]" />
            ) : (
              <ShieldAlert className="h-5 w-5 shrink-0 text-[var(--danger)]" />
            )}
            <div>
              <p
                className={clsx(
                  "text-sm font-semibold",
                  held ? "text-[var(--success)]" : "text-[var(--danger)]",
                )}
              >
                {held
                  ? "Policy boundary held on every probe"
                  : "A probe got past the policy boundary"}
              </p>
              <p className="mt-0.5 text-xs text-[var(--text-secondary)]">
                The AI may be talked into a bad recommendation. The deterministic
                engine is what decides whether it executes.
              </p>
            </div>
          </div>

          <ul className="space-y-2.5">
            {results.map((r, i) => (
              <motion.li
                key={r.name}
                variants={fadeUp}
                initial="hidden"
                animate="show"
                transition={{ delay: i * 0.07 }}
                className="glass rounded-xl p-4"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm font-semibold text-[var(--text-primary)]">
                    {r.name}
                  </span>
                  <Badge tone="neutral">{titleCase(r.attack_type)}</Badge>
                </div>

                <div className="mt-3 grid gap-2.5 sm:grid-cols-2">
                  <Lane
                    icon={Cpu}
                    label="AI agent"
                    status={r.ai_status}
                    body={r.ai_response}
                  />
                  <Lane
                    icon={ShieldCheck}
                    label="Policy engine"
                    status={r.policy_status}
                    body={r.policy_response}
                  />
                </div>
              </motion.li>
            ))}
          </ul>
        </div>
      )}
    </SectionCard>
  );
}

function Lane({
  icon: Icon,
  label,
  status,
  body,
}: {
  icon: typeof Cpu;
  label: string;
  status: string;
  body: string;
}) {
  const ok = status === "passed";
  return (
    <div
      className={clsx(
        "rounded-lg border px-3 py-2.5",
        ok
          ? "border-[rgba(16,217,160,0.26)] bg-[var(--success-dim)]"
          : "border-[rgba(255,90,106,0.26)] bg-[var(--danger-dim)]",
      )}
    >
      <div className="flex items-center gap-1.5">
        <Icon
          className={clsx(
            "h-3.5 w-3.5",
            ok ? "text-[var(--success)]" : "text-[var(--danger)]",
          )}
        />
        <span className="text-[11px] font-semibold uppercase tracking-wider text-[var(--text-secondary)]">
          {label}
        </span>
        {ok ? (
          <CheckCircle2 className="ml-auto h-3.5 w-3.5 text-[var(--success)]" />
        ) : (
          <XCircle className="ml-auto h-3.5 w-3.5 text-[var(--danger)]" />
        )}
      </div>
      <p className="mt-1.5 text-[11px] leading-relaxed text-[var(--text-secondary)]">
        {body}
      </p>
    </div>
  );
}
