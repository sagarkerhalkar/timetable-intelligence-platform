import Link from "next/link";

export default function NotFound() {
  return <section className="error-state"><span aria-hidden="true">404</span><h1>Page not found</h1><p>The requested page is not part of this timetable workspace.</p><Link className="button primary" href="/">Return to overview</Link></section>;
}
