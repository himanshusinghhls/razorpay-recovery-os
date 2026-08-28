"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "@/lib/auth-context";
import { Spinner } from "@/components/ui";

/**
 * Client-side gate for authenticated pages.
 *
 * This is a UX guard, not a security boundary — the API authenticates every
 * request independently, so a user who bypasses this still gets 401s.
 */
export function RequireAuth({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [user, loading, router]);

  if (loading || !user) {
    return (
      <div className="grid min-h-screen place-items-center">
        <Spinner className="h-6 w-6 text-[var(--brand-bright)]" />
      </div>
    );
  }

  return <>{children}</>;
}
