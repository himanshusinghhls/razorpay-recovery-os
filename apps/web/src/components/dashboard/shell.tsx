"use client";

import { motion } from "framer-motion";
import { LucideIcon, LogOut, Sparkles, Zap, CreditCard } from "lucide-react";
import { useState } from "react";
import clsx from "clsx";

import { useAuth, Role } from "@/lib/auth-context";
import { spring } from "@/components/ui";
import { ThemeToggle } from "@/components/ThemeToggle";
import { Logo } from "@/components/Logo";

export interface TabDef {
  key: string;
  label: string;
  icon: LucideIcon;
  badge?: number;
}

const ROLE_TONE: Record<Role, "violet" | "brand" | "neutral"> = {
  admin: "violet",
  analyst: "brand",
  viewer: "neutral",
};

export function DashboardShell({
  tabs,
  active,
  onTabChange,
  children,
}: {
  tabs: TabDef[];
  active: string;
  onTabChange: (key: string) => void;
  children: React.ReactNode;
}) {
  const { user, logout } = useAuth();
  const [signingOut, setSigningOut] = useState(false);

  const initials = (user?.full_name || user?.email || "?")
    .split(/[\s@.]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase())
    .join("");

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 md:px-8">
      <header className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-center gap-3">
          <Logo 
            subtitle={
              <>
                {user?.merchant_name}
                <span className="mx-1.5 opacity-40">·</span>
                <span className="font-mono text-[10px]">{user?.merchant_id}</span>
              </>
            }
          />
        </div>

        <div className="flex flex-wrap items-center gap-4">
          <ThemeToggle />

          <div className="flex items-center gap-2.5 rounded-xl border border-[var(--border-default)] bg-[var(--surface-1)] py-1.5 pl-1.5 pr-3 shadow-sm">
            <div className="grid h-7 w-7 place-items-center rounded-lg bg-gradient-to-br from-[var(--brand)] to-[var(--violet)] text-[11px] font-bold text-white">
              {initials}
            </div>
            <div className="leading-tight">
              <p className="text-xs font-semibold text-[var(--text-primary)]">
                {user?.full_name || user?.email}
              </p>
              <p
                className={clsx(
                  "text-[10px] font-medium uppercase tracking-wide",
                  user && ROLE_TONE[user.role] === "violet"
                    ? "text-[var(--violet)]"
                    : user && ROLE_TONE[user.role] === "brand"
                      ? "text-[var(--brand-bright)]"
                      : "text-[var(--text-muted)]",
                )}
              >
                {user?.role}
              </p>
            </div>
            <button
              onClick={async () => {
                setSigningOut(true);
                await logout();
              }}
              disabled={signingOut}
              title="Sign out"
              aria-label="Sign out"
              className="ml-1 rounded-lg p-1.5 text-[var(--text-muted)] transition hover:bg-[rgba(255,90,106,0.12)] hover:text-[var(--danger)] disabled:opacity-50"
            >
              <LogOut className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      </header>

      <nav className="mt-6 flex gap-1 overflow-x-auto rounded-2xl border border-[var(--border-default)] bg-[var(--surface-1)] p-1.5 backdrop-blur-xl">
        {tabs.map((tab) => {
          const isActive = active === tab.key;
          return (
            <button
              key={tab.key}
              onClick={() => onTabChange(tab.key)}
              className={clsx(
                "relative flex shrink-0 items-center gap-1.5 rounded-xl px-3.5 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "text-white"
                  : "text-[var(--text-muted)] hover:text-[var(--text-secondary)]",
              )}
            >
              {/* One shared element slides between tabs instead of each tab
                  fading its own background in and out. */}
              {isActive && (
                <motion.span
                  layoutId="tab-pill"
                  transition={spring}
                  className="absolute inset-0 rounded-xl bg-gradient-to-b from-[var(--brand-bright)] to-[var(--brand)] shadow-[0_4px_16px_-4px_var(--brand-glow)]"
                />
              )}
              <span className="relative flex items-center gap-1.5">
                <tab.icon className="h-3.5 w-3.5" strokeWidth={2.2} />
                {tab.label}
                {tab.badge ? (
                  <span
                    className={clsx(
                      "ml-0.5 rounded-full px-1.5 py-0.5 text-[10px] font-bold",
                      isActive
                        ? "bg-white/20 text-white"
                        : "bg-[var(--danger-dim)] text-[var(--danger)]",
                    )}
                  >
                    {tab.badge}
                  </span>
                ) : null}
              </span>
            </button>
          );
        })}
      </nav>

      <main className="mt-5">{children}</main>

      <footer className="mt-12 border-t border-[var(--border-subtle)] pt-5 text-center text-[11px] text-[var(--text-muted)]">
        RecoveryOS Enterprise · Every action is policy checked and audit logged
      </footer>
    </div>
  );
}
