"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  AlertCircle,
  ArrowRight,
  Eye,
  EyeOff,
  Lock,
  Mail,
  ShieldCheck,
  Zap,
} from "lucide-react";

import { useAuth } from "@/lib/auth-context";
import { Button, Spinner, ease } from "@/components/ui";

const HIGHLIGHTS = [
  {
    icon: ShieldCheck,
    title: "Deterministic safety boundary",
    body: "The AI proposes. A rules engine disposes. No model output reaches the payment gateway unchecked.",
  },
  {
    icon: Lock,
    title: "Every action is attributable",
    body: "Immutable audit trail per payment, stamped with the user or component responsible.",
  },
  {
    icon: Zap,
    title: "Bounded autonomous recovery",
    body: "Retry limits, 72-hour windows and per-customer daily caps enforced before execution.",
  },
];

export default function LoginPage() {
  const { login, user, loading } = useAuth();
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Already signed in (e.g. the refresh cookie was still valid) — don't make
  // the user look at a login form they don't need.
  useEffect(() => {
    if (!loading && user) router.replace("/dashboard");
  }, [loading, user, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email.trim(), password);
      router.replace("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to sign in");
      setPassword("");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="grid min-h-screen place-items-center">
        <Spinner className="h-6 w-6 text-[var(--brand-bright)]" />
      </div>
    );
  }

  return (
    <div className="grid min-h-screen lg:grid-cols-[1.05fr_1fr]">
      {/* Narrative panel — hidden on small screens where the form is the job. */}
      <motion.aside
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.6 }}
        className="relative hidden flex-col justify-between overflow-hidden border-r border-[var(--border-subtle)] p-12 lg:flex"
      >
        <div className="flex items-center gap-3">
          <div className="relative grid h-10 w-10 place-items-center rounded-xl bg-gradient-to-br from-[var(--brand-bright)] to-[var(--brand)] shadow-[0_8px_24px_-8px_var(--brand-glow)]">
            <Zap className="h-5 w-5 text-white" strokeWidth={2.4} />
          </div>
          <div>
            <p className="text-base font-bold tracking-tight">RecoveryOS</p>
            <p className="text-xs text-[var(--text-muted)]">
              Autonomous Revenue Recovery
            </p>
          </div>
        </div>

        <div className="max-w-lg">
          <motion.h1
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ ...ease, delay: 0.1 }}
            className="text-4xl font-bold leading-[1.15] tracking-tight"
          >
            Recover failed payments{" "}
            <span className="bg-gradient-to-r from-[var(--brand-bright)] via-[#7ba6ff] to-[var(--violet)] bg-clip-text text-transparent">
              without losing control
            </span>
            .
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ ...ease, delay: 0.18 }}
            className="mt-4 text-sm leading-relaxed text-[var(--text-secondary)]"
          >
            An AI analyst diagnoses every failure. A deterministic policy engine
            decides what is allowed to happen next. Every step is written to an
            immutable audit trail.
          </motion.p>

          <div className="mt-10 space-y-5">
            {HIGHLIGHTS.map((item, i) => (
              <motion.div
                key={item.title}
                initial={{ opacity: 0, x: -14 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ ...ease, delay: 0.26 + i * 0.08 }}
                className="flex gap-3.5"
              >
                <div className="mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-lg border border-[rgba(43,106,255,0.32)] bg-[rgba(43,106,255,0.12)]">
                  <item.icon
                    className="h-4 w-4 text-[var(--brand-bright)]"
                    strokeWidth={2.1}
                  />
                </div>
                <div>
                  <p className="text-sm font-semibold text-[var(--text-primary)]">
                    {item.title}
                  </p>
                  <p className="mt-0.5 text-xs leading-relaxed text-[var(--text-muted)]">
                    {item.body}
                  </p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>

        <p className="text-xs text-[var(--text-muted)]">
          Razorpay AI Buildathon · Track 03
        </p>
      </motion.aside>

      {/* Form panel */}
      <div className="flex items-center justify-center px-6 py-12">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={ease}
          className="w-full max-w-sm"
        >
          <div className="mb-8 lg:hidden">
            <div className="mb-4 grid h-11 w-11 place-items-center rounded-xl bg-gradient-to-br from-[var(--brand-bright)] to-[var(--brand)]">
              <Zap className="h-5 w-5 text-white" strokeWidth={2.4} />
            </div>
            <p className="text-lg font-bold tracking-tight">RecoveryOS</p>
          </div>

          <h2 className="text-2xl font-bold tracking-tight">Sign in</h2>
          <p className="mt-1.5 text-sm text-[var(--text-muted)]">
            Access your merchant recovery console.
          </p>

          <form onSubmit={handleSubmit} className="mt-8 space-y-4">
            <Field
              id="email"
              label="Work email"
              icon={Mail}
              type="email"
              value={email}
              onChange={setEmail}
              placeholder="you@company.in"
              autoComplete="username"
              required
            />

            <div>
              <label
                htmlFor="password"
                className="mb-1.5 block text-xs font-medium text-[var(--text-secondary)]"
              >
                Password
              </label>
              <div className="relative">
                <Lock className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--text-muted)]" />
                <input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••"
                  autoComplete="current-password"
                  required
                  className="w-full rounded-xl border border-[var(--border-default)] bg-[var(--surface-1)] py-2.5 pl-10 pr-10 text-sm text-[var(--text-primary)] outline-none transition placeholder:text-[var(--text-muted)] focus:border-[var(--brand)] focus:bg-[var(--surface-2)]"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)] transition hover:text-[var(--text-secondary)]"
                >
                  {showPassword ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </button>
              </div>
            </div>

            <AnimatePresence mode="wait">
              {error && (
                <motion.div
                  key={error}
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.2 }}
                  role="alert"
                  className="flex items-start gap-2 overflow-hidden rounded-xl border border-[rgba(255,90,106,0.32)] bg-[var(--danger-dim)] px-3 py-2.5"
                >
                  <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-[var(--danger)]" />
                  <p className="text-xs text-[var(--danger)]">{error}</p>
                </motion.div>
              )}
            </AnimatePresence>

            <Button
              type="submit"
              loading={submitting}
              icon={ArrowRight}
              className="w-full"
            >
              {submitting ? "Signing in…" : "Sign in"}
            </Button>
          </form>

          <p className="mt-8 text-center text-[11px] leading-relaxed text-[var(--text-muted)]">
            Sessions use short-lived access tokens with a rotating, httpOnly
            refresh cookie. Repeated failed attempts lock the account.
          </p>
        </motion.div>
      </div>
    </div>
  );
}

function Field({
  id,
  label,
  icon: Icon,
  type,
  value,
  onChange,
  placeholder,
  autoComplete,
  required,
}: {
  id: string;
  label: string;
  icon: typeof Mail;
  type: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  autoComplete?: string;
  required?: boolean;
}) {
  return (
    <div>
      <label
        htmlFor={id}
        className="mb-1.5 block text-xs font-medium text-[var(--text-secondary)]"
      >
        {label}
      </label>
      <div className="relative">
        <Icon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--text-muted)]" />
        <input
          id={id}
          type={type}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          autoComplete={autoComplete}
          required={required}
          className="w-full rounded-xl border border-[var(--border-default)] bg-[var(--surface-1)] py-2.5 pl-10 pr-3 text-sm text-[var(--text-primary)] outline-none transition placeholder:text-[var(--text-muted)] focus:border-[var(--brand)] focus:bg-[var(--surface-2)]"
        />
      </div>
    </div>
  );
}
