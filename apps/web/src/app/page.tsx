"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "@/lib/auth-context";
import { Spinner } from "@/components/ui";

/**
 * Entry point. Sends the visitor to the console or to login once the initial
 * silent refresh has settled, so a returning user with a valid cookie never
 * sees the login form flash.
 */
export default function Home() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;
    router.replace(user ? "/dashboard" : "/login");
  }, [user, loading, router]);

  return (
    <div className="grid min-h-screen place-items-center">
      <Spinner className="h-6 w-6 text-[var(--brand-bright)]" />
    </div>
  );
}
