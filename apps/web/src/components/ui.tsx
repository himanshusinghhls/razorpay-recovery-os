"use client";

import { motion, useMotionValue, useSpring, useTransform } from "framer-motion";
import { LucideIcon } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import clsx from "clsx";

export const spring = { type: "spring" as const, stiffness: 320, damping: 30 };
export const softSpring = { type: "spring" as const, stiffness: 180, damping: 24 };
export const ease = { duration: 0.35, ease: [0.22, 1, 0.36, 1] as const };

export const fadeUp = {
  hidden: { opacity: 0, y: 14 },
  show: { opacity: 1, y: 0, transition: ease },
};

export const staggerChildren = {
  hidden: {},
  show: { transition: { staggerChildren: 0.06, delayChildren: 0.04 } },
};

export type Tone = "brand" | "success" | "warning" | "danger" | "violet" | "neutral";

const TONE_TEXT: Record<Tone, string> = {
  brand: "text-[var(--brand-bright)]",
  success: "text-[var(--success)]",
  warning: "text-[var(--warning)]",
  danger: "text-[var(--danger)]",
  violet: "text-[var(--violet)]",
  neutral: "text-[var(--text-secondary)]",
};

const TONE_BG: Record<Tone, string> = {
  brand: "bg-[rgba(43,106,255,0.14)] border-[rgba(43,106,255,0.32)]",
  success: "bg-[var(--success-dim)] border-[rgba(16,217,160,0.32)]",
  warning: "bg-[var(--warning-dim)] border-[rgba(245,165,36,0.32)]",
  danger: "bg-[var(--danger-dim)] border-[rgba(255,90,106,0.32)]",
  violet: "bg-[var(--violet-dim)] border-[rgba(139,124,255,0.32)]",
  neutral: "bg-[rgba(126,160,235,0.08)] border-[var(--border-default)]",
};

export const toneText = (t: Tone) => TONE_TEXT[t];
export const toneChip = (t: Tone) => clsx(TONE_BG[t], TONE_TEXT[t]);

export function Badge({
  tone = "neutral",
  icon: Icon,
  children,
  pulse,
  className,
}: {
  tone?: Tone;
  icon?: LucideIcon;
  children: React.ReactNode;
  pulse?: boolean;
  className?: string;
}) {
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-medium tracking-tight",
        toneChip(tone),
        className,
      )}
    >
      {pulse && (
        <span className="relative inline-flex h-1.5 w-1.5">
          <span className="pulse-ring absolute inset-0 rounded-full" />
          <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-current" />
        </span>
      )}
      {Icon && <Icon className="h-3 w-3" strokeWidth={2.2} />}
      {children}
    </span>
  );
}

export function Button({
  children,
  onClick,
  disabled,
  loading,
  variant = "primary",
  icon: Icon,
  type = "button",
  className,
  title,
}: {
  children: React.ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  loading?: boolean;
  variant?: "primary" | "ghost" | "danger" | "success";
  icon?: LucideIcon;
  type?: "button" | "submit";
  className?: string;
  title?: string;
}) {
  const base =
    "relative inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-50 overflow-hidden";

  const variants = {
    primary:
      "bg-gradient-to-b from-[var(--brand-bright)] to-[var(--brand)] text-white shadow-[0_6px_20px_-6px_var(--brand-glow)] hover:from-[#6b9dff] hover:to-[#3d78ff]",
    ghost:
      "border border-[var(--border-default)] bg-[var(--surface-1)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:border-[var(--border-strong)]",
    danger:
      "border border-[rgba(255,90,106,0.35)] bg-[var(--danger-dim)] text-[var(--danger)] hover:bg-[rgba(255,90,106,0.22)]",
    success:
      "border border-[rgba(16,217,160,0.35)] bg-[var(--success-dim)] text-[var(--success)] hover:bg-[rgba(16,217,160,0.22)]",
  };

  return (
    <motion.button
      type={type}
      title={title}
      onClick={onClick}
      disabled={disabled || loading}
      whileHover={disabled || loading ? undefined : { y: -1 }}
      whileTap={disabled || loading ? undefined : { scale: 0.98 }}
      transition={spring}
      className={clsx(base, variants[variant], className)}
    >
      {loading ? (
        <Spinner className="h-4 w-4" />
      ) : (
        Icon && <Icon className="h-4 w-4" strokeWidth={2.2} />
      )}
      <span>{children}</span>
      {variant === "primary" && !disabled && !loading && (
        <span className="shimmer pointer-events-none absolute inset-0" />
      )}
    </motion.button>
  );
}

export function Spinner({ className }: { className?: string }) {
  return (
    <svg className={clsx("animate-spin", className)} viewBox="0 0 24 24" fill="none">
      <circle
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="3"
        className="opacity-25"
      />
      <path
        d="M22 12a10 10 0 0 1-10 10"
        stroke="currentColor"
        strokeWidth="3"
        strokeLinecap="round"
      />
    </svg>
  );
}

export function TiltCard({
  children,
  className,
  disabled,
}: {
  children: React.ReactNode;
  className?: string;
  disabled?: boolean;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const x = useMotionValue(0);
  const y = useMotionValue(0);

  const rotateX = useSpring(useTransform(y, [-0.5, 0.5], [6, -6]), softSpring);
  const rotateY = useSpring(useTransform(x, [-0.5, 0.5], [-6, 6]), softSpring);

  return (
    <motion.div
      ref={ref}
      onPointerMove={(e) => {
        if (disabled || e.pointerType !== "mouse" || !ref.current) return;
        const rect = ref.current.getBoundingClientRect();
        x.set((e.clientX - rect.left) / rect.width - 0.5);
        y.set((e.clientY - rect.top) / rect.height - 0.5);
      }}
      onPointerLeave={() => {
        x.set(0);
        y.set(0);
      }}
      style={{ rotateX, rotateY, transformPerspective: 900 }}
      className={clsx("glass glass-sheen", className)}
    >
      {children}
    </motion.div>
  );
}

export function AnimatedNumber({
  value,
  format,
  className,
}: {
  value: number;
  format?: (n: number) => string;
  className?: string;
}) {
  const spring_ = useSpring(0, { stiffness: 90, damping: 20 });
  const [display, setDisplay] = useState(value);

  useEffect(() => {
    spring_.set(value);
  }, [value, spring_]);

  useEffect(() => spring_.on("change", (v) => setDisplay(v)), [spring_]);

  return (
    <span className={className}>
      {format ? format(display) : Math.round(display).toLocaleString("en-IN")}
    </span>
  );
}

export function MetricTile({
  label,
  value,
  icon: Icon,
  tone = "brand",
  hint,
  loading,
}: {
  label: string;
  value: string | number;
  icon: LucideIcon;
  tone?: Tone;
  hint?: string;
  loading?: boolean;
}) {
  return (
    <motion.div
      variants={fadeUp}
      whileHover={{ scale: 1.02, y: -4, rotateX: 2 }}
      transition={{ type: "spring", stiffness: 320, damping: 25 }}
      className="glass glass-sheen rounded-2xl p-4 cursor-default"
    >
      <div className="flex items-center gap-2.5">
        <div
          className={clsx(
            "grid h-8 w-8 place-items-center rounded-lg border",
            toneChip(tone),
          )}
        >
          <Icon className="h-4 w-4" strokeWidth={2.2} />
        </div>
        <span className="text-[11px] font-medium uppercase tracking-wider text-[var(--text-muted)]">
          {label}
        </span>
      </div>

      <div className="mt-3 flex items-baseline gap-2">
        {loading ? (
          <div className="h-7 w-16 animate-pulse rounded bg-[rgba(126,160,235,0.14)]" />
        ) : (
          <span className="text-2xl font-bold tracking-tight text-[var(--text-primary)]">
            {typeof value === "number" ? (
              <AnimatedNumber value={value} />
            ) : (
              value
            )}
          </span>
        )}
        {hint && (
          <span className="text-[11px] text-[var(--text-muted)]">{hint}</span>
        )}
      </div>
    </motion.div>
  );
}

export function SectionCard({
  title,
  description,
  icon: Icon,
  action,
  children,
  className,
}: {
  title: string;
  description?: string;
  icon?: LucideIcon;
  action?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <motion.section
      variants={fadeUp}
      className={clsx("glass glass-sheen rounded-2xl", className)}
    >
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--border-subtle)] px-5 py-4">
        <div className="flex items-center gap-2.5">
          {Icon && (
            <Icon
              className="h-4 w-4 text-[var(--brand-bright)]"
              strokeWidth={2.2}
            />
          )}
          <div>
            <h2 className="text-sm font-semibold tracking-tight text-[var(--text-primary)]">
              {title}
            </h2>
            {description && (
              <p className="mt-0.5 text-xs text-[var(--text-muted)]">
                {description}
              </p>
            )}
          </div>
        </div>
        {action}
      </header>
      <div className="p-5">{children}</div>
    </motion.section>
  );
}

export function EmptyState({
  icon: Icon,
  title,
  description,
}: {
  icon: LucideIcon;
  title: string;
  description?: string;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-12 text-center">
      <div className="grid h-12 w-12 place-items-center rounded-xl border border-[var(--border-default)] bg-[var(--surface-1)]">
        <Icon className="h-5 w-5 text-[var(--text-muted)]" strokeWidth={1.8} />
      </div>
      <div>
        <p className="text-sm font-medium text-[var(--text-secondary)]">{title}</p>
        {description && (
          <p className="mt-1 text-xs text-[var(--text-muted)]">{description}</p>
        )}
      </div>
    </div>
  );
}

export function SkeletonRows({ rows = 4 }: { rows?: number }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className="h-14 animate-pulse rounded-xl bg-[rgba(126,160,235,0.08)]"
          style={{ animationDelay: `${i * 80}ms` }}
        />
      ))}
    </div>
  );
}

export function Mono({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <code
      className={clsx(
        "rounded bg-[rgba(126,160,235,0.10)] px-1.5 py-0.5 font-mono text-[11px] text-[var(--text-secondary)]",
        className,
      )}
    >
      {children}
    </code>
  );
}
