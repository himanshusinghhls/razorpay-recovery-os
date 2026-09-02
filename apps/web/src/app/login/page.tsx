"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { AlertCircle, ArrowRight, Eye, EyeOff, Lock, Mail } from "lucide-react";

import { useAuth } from "@/lib/auth-context";
import { Button, Spinner, ease } from "@/components/ui";
import { Logo } from "@/components/Logo";
import Link from "next/link";
import { ThemeToggle } from "@/components/ThemeToggle";

export default function LoginPage() {
  const { login, user, loading } = useAuth();
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

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
    <div className="relative min-h-screen overflow-hidden flex flex-col items-center justify-center p-6">
      <header className="absolute inset-x-0 top-0 z-50 flex items-center justify-between p-6 md:px-12">
        <Link href="/">
          <Logo />
        </Link>
        <ThemeToggle />
      </header>

      <motion.div
        initial={{ opacity: 0, scale: 0.98, y: 10 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        transition={{ ...ease, duration: 0.6 }}
        className="w-full max-w-[400px]"
      >
        <div className="glass p-8 sm:p-10 rounded-3xl shadow-xl border border-[var(--border-default)]">
          <div className="mb-8 text-center flex flex-col items-center">
            <h2 className="text-2xl font-bold tracking-tight text-[var(--text-primary)]">
              Welcome back
            </h2>
            <p className="mt-2 text-sm text-[var(--text-muted)]">
              Access your merchant recovery console
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
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
                  className="w-full rounded-xl border border-[var(--border-default)] bg-[var(--surface-1)] py-2.5 pl-10 pr-10 text-sm text-[var(--text-primary)] outline-none transition placeholder:text-[var(--text-muted)] focus:border-[var(--brand)] focus:bg-[var(--surface-2)] shadow-inner"
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
              className="mt-2 w-full"
            >
              {submitting ? "Signing in…" : "Sign in"}
            </Button>
          </form>
        </div>

        <p className="mt-8 text-center text-[11px] leading-relaxed text-[var(--text-muted)] max-w-xs mx-auto">
          Sessions use short-lived access tokens with a rotating, httpOnly
          refresh cookie.
        </p>
      </motion.div>
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
          className="w-full rounded-xl border border-[var(--border-default)] bg-[var(--surface-1)] py-2.5 pl-10 pr-3 text-sm text-[var(--text-primary)] outline-none transition placeholder:text-[var(--text-muted)] focus:border-[var(--brand)] focus:bg-[var(--surface-2)] shadow-inner"
        />
      </div>
    </div>
  );
}
