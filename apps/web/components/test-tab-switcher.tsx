"use client";

import { useEffect, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

type Props = Readonly<{
  selectedTab: string;
  counts: Record<string, number>;
  total: number;
}>;

export function TestTabSwitcher({ selectedTab, counts, total }: Props) {
  const router = useRouter();
  const [pendingTab, setPendingTab] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  useEffect(() => setPendingTab(null), [selectedTab]);

  const activeTab = pendingTab ?? selectedTab;
  const navigating = pendingTab !== null && pendingTab !== selectedTab;

  function hrefFor(tab: string): string {
    return tab ? `/tests?tab=${encodeURIComponent(tab)}` : "/tests";
  }

  function warmTab(tab: string) {
    router.prefetch(hrefFor(tab));
  }

  function changeTab(tab: string) {
    if (tab === activeTab) return;
    setPendingTab(tab);
    startTransition(() => router.replace(hrefFor(tab), { scroll: false }));
  }

  const entries = Object.entries(counts).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));

  return (
    <div className="test-tab-switcher-wrap" aria-busy={navigating || isPending}>
      <div className="test-tab-switcher" role="tablist" aria-label="Test Series tab filter">
        <button
          type="button"
          role="tab"
          aria-selected={!activeTab}
          className={!activeTab ? `active${navigating ? " pending" : ""}` : ""}
          disabled={navigating && !activeTab}
          onMouseEnter={() => warmTab("")}
          onFocus={() => warmTab("")}
          onClick={() => changeTab("")}
        >
          All tests <b>{total}</b>
        </button>
        {entries.map(([name, count]) => {
          const active = activeTab === name;
          return (
            <button
              type="button"
              role="tab"
              aria-selected={active}
              className={active ? `active${navigating ? " pending" : ""}` : ""}
              disabled={navigating && active}
              key={name}
              onMouseEnter={() => warmTab(name)}
              onFocus={() => warmTab(name)}
              onClick={() => changeTab(name)}
            >
              {name} <b>{count}</b>
            </button>
          );
        })}
      </div>
      <span className="test-tab-loading" aria-live="polite">
        {navigating || isPending
          ? `Opening ${pendingTab || "all tests"}… one click accepted`
          : selectedTab
            ? `Showing ${selectedTab}`
            : "Showing all monitored tests"}
      </span>
    </div>
  );
}
