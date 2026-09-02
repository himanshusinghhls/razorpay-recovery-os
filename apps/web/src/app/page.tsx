"use client";

import { motion } from "framer-motion";
import { ArrowRight, ShieldCheck, Zap, Lock } from "lucide-react";
import Link from "next/link";
import { Logo } from "@/components/Logo";
import { ThemeToggle } from "@/components/ThemeToggle";
import { ease } from "@/components/ui";

const HIGHLIGHTS = [
  {
    icon: ShieldCheck,
    title: "Deterministic Guardrails",
    body: "No model output reaches the payment gateway unchecked. Every AI proposal is validated against strict boundaries.",
  },
  {
    icon: Lock,
    title: "Immutable Audit Logs",
    body: "An immutable trail records every execution, policy check, and human escalation.",
  },
  {
    icon: Zap,
    title: "Autonomous Execution",
    body: "Safely execute retries, send alerts, or route failed payments for review in real-time.",
  },
];

export default function Home() {
  return (
    <div className="relative min-h-screen overflow-hidden flex flex-col">
      <header className="absolute inset-x-0 top-0 z-50 flex items-center justify-between p-6 md:px-12">
        <Logo />
        <div className="flex items-center gap-4">
          <ThemeToggle />
          <Link
            href="/login"
            className="rounded-full bg-[var(--surface-1)] border border-[var(--border-default)] px-4 py-1.5 text-sm font-medium text-[var(--text-primary)] transition hover:bg-[var(--surface-2)] shadow-sm"
          >
            Sign In
          </Link>
        </div>
      </header>

      <main className="flex-1 flex flex-col items-center justify-center px-6 pt-32 pb-20 z-10 text-center">
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          transition={{ duration: 0.8, ease: "easeOut" }}
          className="max-w-4xl"
        >
          <h1 className="text-5xl md:text-7xl font-bold tracking-tight text-[var(--text-primary)] leading-[1.1]">
            Revenue recovery, <br />
            <span className="bg-gradient-to-r from-[var(--brand-bright)] via-[#7ba6ff] to-[var(--violet)] bg-clip-text text-transparent">
              engineered for trust
            </span>
          </h1>
          <p className="mt-6 text-lg md:text-xl text-[var(--text-secondary)] max-w-2xl mx-auto leading-relaxed">
            RecoveryOS is an enterprise-grade fintech platform. An AI analyst diagnoses failed payments, while a deterministic policy engine strictly controls execution.
          </p>

          <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link href="/login">
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="flex items-center gap-2 rounded-full bg-gradient-to-r from-[var(--brand)] to-[var(--brand-bright)] px-8 py-3.5 text-sm font-semibold text-white shadow-[0_8px_24px_-8px_var(--brand-glow)]"
              >
                Access Console
                <ArrowRight className="h-4 w-4" />
              </motion.button>
            </Link>
          </div>
        </motion.div>

        <div className="mt-24 grid md:grid-cols-3 gap-6 max-w-5xl mx-auto">
          {HIGHLIGHTS.map((item, i) => (
            <motion.div
              key={item.title}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 + i * 0.1, ...ease }}
              whileHover={{ y: -5, scale: 1.02, rotateX: 2 }}
              className="glass p-6 rounded-2xl text-left border border-[var(--border-default)] shadow-sm cursor-default"
            >
              <div className="mb-4 grid h-10 w-10 place-items-center rounded-xl bg-gradient-to-br from-[var(--brand)] to-[var(--violet)] bg-opacity-10 shadow-sm text-white">
                <item.icon className="h-5 w-5" strokeWidth={2.2} />
              </div>
              <h3 className="text-lg font-semibold text-[var(--text-primary)]">{item.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-[var(--text-muted)]">{item.body}</p>
            </motion.div>
          ))}
        </div>
      </main>
    </div>
  );
}
