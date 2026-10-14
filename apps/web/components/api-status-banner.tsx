"use client";

import { useEffect, useState } from "react";

export function ApiStatusBanner() {
  const [offline, setOffline] = useState(false);

  useEffect(() => {
    let active = true;
    async function check() {
      try {
        const response = await fetch("/backend/api/v1/health", {
          cache: "no-store",
          signal: AbortSignal.timeout(5000)
        });
        if (active) setOffline(!response.ok);
      } catch {
        if (active) setOffline(true);
      }
    }
    void check();
    const timer = window.setInterval(check, 30000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, []);

  if (!offline) return null;
  return (
    <div className="api-status-banner" role="alert">
      <strong>The local data service is not responding.</strong>
      <span>Timetable, Google Sheet and content pages may look empty. Restart the local server, then refresh this page.</span>
    </div>
  );
}
