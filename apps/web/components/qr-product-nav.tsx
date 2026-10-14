"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { resolveActiveNavigationHref } from "@/lib/navigation";

const tabs = [
  { href: "/qr", label: "New QR", icon: "＋" },
  { href: "/qr/templates", label: "Templates", icon: "◫" },
  { href: "/qr/bulk", label: "Bulk Create", icon: "▦" },
  { href: "/qr/codes", label: "My QR Codes", icon: "⌗" },
  { href: "/qr/stats", label: "Analytics", icon: "▥" },
  { href: "/qr/reports", label: "Geo & Devices", icon: "◎" }
] as const;

const tabHrefs = tabs.map((tab) => tab.href);

export function QrProductNav() {
  const pathname = usePathname();
  const [pendingHref, setPendingHref] = useState<string | null>(null);
  const resolvedHref = resolveActiveNavigationHref(pathname, tabHrefs);
  const activeHref = pendingHref ?? resolvedHref;

  useEffect(() => {
    setPendingHref(null);
  }, [pathname]);

  return (
    <nav className="qrfy-product-nav" aria-label="QR Studio">
      <div className="qrfy-product-brand">
        <span className="qrfy-product-logo">QR</span>
        <div><strong>NextToppers QR</strong><small>Fast, secure QR & verified scan intelligence</small></div>
      </div>
      <div className="qrfy-product-tabs">
        {tabs.map((tab) => {
          const active = tab.href === activeHref;
          const pending = pendingHref === tab.href;
          return (
            <Link
              key={tab.href}
              href={tab.href}
              prefetch
              onClick={(event) => {
                setPendingHref(tab.href);
                const details = event.currentTarget.closest("details.mobile-menu") as HTMLDetailsElement | null;
                if (details) details.open = false;
              }}
              className={`${active ? "active" : ""}${pending ? " pending" : ""}`.trim()}
              aria-current={active ? "page" : undefined}
              aria-busy={pending ? "true" : undefined}
            >
              <span aria-hidden="true">{pending ? "·" : tab.icon}</span>{tab.label}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}

