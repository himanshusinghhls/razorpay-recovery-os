"use client";

import { useTheme } from "next-themes";
import { Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import clsx from "clsx";

export function ThemeToggle({ className }: { className?: string }) {
  const { resolvedTheme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => setMounted(true), []);

  if (!mounted) {
    return <div className={clsx("h-9 w-16 rounded-full bg-[var(--surface-2)]", className)} />;
  }

  const isDark = resolvedTheme === "dark";

  return (
    <button
      onClick={() => setTheme(isDark ? "light" : "dark")}
      className={clsx(
        "relative flex h-9 w-16 items-center rounded-full border border-[var(--border-default)] p-1 transition-colors hover:border-[var(--brand)]",
        isDark ? "bg-[var(--bg-raised)]" : "bg-white shadow-inner",
        className
      )}
      aria-label="Toggle theme"
    >
      <motion.div
        className="flex h-7 w-7 items-center justify-center rounded-full bg-gradient-to-br from-[var(--brand-bright)] to-[var(--brand)] shadow-sm text-white"
        layout
        initial={false}
        animate={{
          x: isDark ? 26 : 0,
          rotate: isDark ? 360 : 0
        }}
        transition={{ type: "spring", stiffness: 400, damping: 25 }}
      >
        {isDark ? (
          <Moon className="h-3.5 w-3.5" strokeWidth={2.5} />
        ) : (
          <Sun className="h-4 w-4" strokeWidth={2.5} />
        )}
      </motion.div>
    </button>
  );
}
