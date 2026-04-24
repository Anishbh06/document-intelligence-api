"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { isAuthenticated } from "@/lib/auth";

/**
 * Wraps any client page that requires authentication.
 * Immediately redirects to /login if no JWT token is found in localStorage.
 */
export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/login");
    }
  }, [router]);

  if (typeof window !== "undefined" && !isAuthenticated()) {
    return null; // prevent flash of protected content while redirecting
  }

  return <>{children}</>;
}
