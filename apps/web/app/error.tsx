"use client";

export default function ErrorPage({ reset }: Readonly<{ error: Error & { digest?: string }; reset: () => void }>) {
  return <section className="error-state"><span aria-hidden="true">!</span><h1>Something did not load correctly</h1><p>Your data is safe. Retry this page or check the API health status.</p><button className="button primary" onClick={reset} type="button">Try again</button></section>;
}
