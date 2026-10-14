"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export function PageAutoRefresh({ minutes = 5 }: Readonly<{ minutes?: number }>) {
  const router = useRouter();
  useEffect(() => {
    const refresh = () => {
      if (document.visibilityState === "visible") router.refresh();
    };
    const timer = window.setInterval(refresh, Math.max(1, minutes) * 60_000);
    window.addEventListener("focus", refresh);
    return () => {
      window.clearInterval(timer);
      window.removeEventListener("focus", refresh);
    };
  }, [minutes, router]);
  return null;
}
