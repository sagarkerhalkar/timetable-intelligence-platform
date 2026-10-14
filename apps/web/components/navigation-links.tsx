"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { navigation, resolveActiveNavigationHref } from "@/lib/navigation";

export function NavigationLinks({ mobile = false }: { mobile?: boolean }) {
  const pathname = usePathname();
  const [pendingHref, setPendingHref] = useState<string | null>(null);
  const items = mobile ? navigation.slice(0, 5) : navigation;
  const resolvedHref = resolveActiveNavigationHref(pathname);
  const activeHref = pendingHref ?? resolvedHref;

  useEffect(() => {
    setPendingHref(null);
  }, [pathname]);

  return (
    <>
      {items.map((item) => {
        const [label, href, icon] = item;
        const active = href === activeHref;
        return (
          <Link
            className={`${active ? "active" : ""}${pendingHref === href ? " pending" : ""}`.trim() || undefined}
            href={href}
            key={href}
            aria-current={active ? "page" : undefined}
            aria-busy={pendingHref === href ? "true" : undefined}
            onClick={(event) => {
              setPendingHref(href);
              const details = event.currentTarget.closest("details.mobile-menu") as HTMLDetailsElement | null;
              if (details) details.open = false;
            }}
            prefetch
          >
            <span aria-hidden="true">{icon}</span>
            {mobile ? <small>{label.split(" ")[0]}</small> : label}
          </Link>
        );
      })}
    </>
  );
}
