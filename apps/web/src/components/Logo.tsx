"use client";

import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { API_BASE } from "@/lib/api";

export function Logo({ className, showText = true, subtitle }: { className?: string, showText?: boolean, subtitle?: React.ReactNode }) {
  const [isHealthy, setIsHealthy] = useState(false);

  useEffect(() => {
    let mounted = true;
    const checkHealth = async () => {
      try {
        const res = await fetch(API_BASE.replace('/api/v1', '/health'));
        if (res.ok && mounted) {
          setIsHealthy(true);
        } else if (mounted) {
          setIsHealthy(false);
        }
      } catch {
        if (mounted) setIsHealthy(false);
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  return (
    <div className={`flex items-center gap-3 ${className || ""}`}>
      <motion.div
        className="relative grid h-10 w-10 place-items-center rounded-xl bg-gradient-to-br from-[var(--brand-bright)] to-[var(--brand)] shadow-[0_8px_24px_-8px_var(--brand-glow)] ring-1 ring-white/20"
        whileHover={{ scale: 1.05, rotateZ: 5 }}
        whileTap={{ scale: 0.95 }}
        transition={{ type: "spring", stiffness: 400, damping: 25 }}
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="text-white drop-shadow-sm"
        >
          <motion.path
            d="m12 3-8 4.5 8 4.5 8-4.5Z"
            initial={{ pathLength: 0 }}
            animate={{ pathLength: 1 }}
            transition={{ duration: 1.5, ease: "easeInOut" }}
          />
          <motion.path
            d="M4 12v6l8 4.5 8-4.5v-6"
            initial={{ pathLength: 0 }}
            animate={{ pathLength: 1 }}
            transition={{ duration: 1.5, delay: 0.2, ease: "easeInOut" }}
          />
          <motion.path
            d="m4 16.5 8 4.5 8-4.5"
            initial={{ pathLength: 0 }}
            animate={{ pathLength: 1 }}
            transition={{ duration: 1.5, delay: 0.4, ease: "easeInOut" }}
          />
          <motion.path
            d="m12 12 8-4.5"
            initial={{ pathLength: 0 }}
            animate={{ pathLength: 1 }}
            transition={{ duration: 1.5, delay: 0.6, ease: "easeInOut" }}
          />
        </svg>
        {isHealthy && (
          <motion.span
            animate={{ scale: [1, 1.2, 1], opacity: [0.8, 1, 0.8] }}
            transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
            className="absolute -right-0.5 -top-0.5 h-3 w-3 rounded-full border-2 border-[var(--bg-base)] bg-[var(--success)] shadow-[0_0_8px_var(--success)]"
          />
        )}
      </motion.div>
      {showText && (
        <div className="flex flex-col justify-center">
          <h1 className="text-lg font-bold leading-tight tracking-tight text-[var(--text-primary)]">
            Recovery<span className="text-[var(--brand-bright)]">OS</span>
          </h1>
          {subtitle && <div className="text-xs text-[var(--text-muted)] mt-0.5">{subtitle}</div>}
        </div>
      )}
    </div>
  );
}
