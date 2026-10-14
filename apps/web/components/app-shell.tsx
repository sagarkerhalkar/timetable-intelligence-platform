import Link from "next/link";
import { NavigationLinks } from "@/components/navigation-links";
import { ThemeToggle } from "@/components/theme-toggle";
import { ApiStatusBanner } from "@/components/api-status-banner";
import { navigation } from "@/lib/navigation";

export function AppShell({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="Primary navigation">
        <Link className="brand" href="/" aria-label="Timetable home">
          <span className="brand-mark" aria-hidden="true">TT</span>
          <span><strong>Daily Timetable</strong><small>Sheets, classes and content</small></span>
        </Link>
        <nav className="desktop-nav"><NavigationLinks /></nav>
        <div className="sync-card" aria-label="How the app works">
          <span className="pulse" aria-hidden="true" />
          <strong>Simple view enabled</strong>
          <small>Start with Today. Every page uses plain words; technical proof stays hidden.</small>
          <small><b>Installed build: v1.0.11.1</b></small>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <details className="mobile-menu">
            <summary aria-label="Open navigation">☰ <span>Menu</span></summary>
            <nav>
              {navigation.map(([label, href]) => <Link href={href} key={href}>{label}</Link>)}
            </nav>
          </details>
          <form className="global-search" role="search" action="/content" method="get">
            <span aria-hidden="true">⌕</span>
            <label className="sr-only" htmlFor="global-search">Search videos, PDFs, subjects and topics</label>
            <input id="global-search" name="q" placeholder="Search topic, subject, teacher, or paste a Drive link…" />
            <button type="submit">Search</button>
          </form>
          <ThemeToggle />
        </header>
        <ApiStatusBanner />
        <main id="main-content" className="main-content" tabIndex={-1}>{children}</main>
        <nav className="mobile-bottom-nav" aria-label="Mobile primary navigation"><NavigationLinks mobile /></nav>
      </div>
    </div>
  );
}
