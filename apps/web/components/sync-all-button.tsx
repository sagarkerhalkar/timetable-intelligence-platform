"use client";

import { useRef, useState } from "react";
import { PUBLIC_API_URL } from "@/lib/api";
import type { SheetSource } from "@/lib/types";

const ACTIVE_STATES = new Set(["queued", "downloading", "analyzing"]);

function wait(milliseconds: number) {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
}

export function SyncAllButton() {
  const [state, setState] = useState<"idle" | "working" | "done" | "error">("idle");
  const [message, setMessage] = useState("Check every connected Google Sheet and compare it with the previous saved version.");
  const cancelled = useRef(false);

  async function readSources(): Promise<SheetSource[]> {
    const response = await fetch(`${PUBLIC_API_URL}/api/v1/sources`, { cache: "no-store" });
    if (!response.ok) throw new Error("Could not read Google Sheet progress");
    return response.json() as Promise<SheetSource[]>;
  }

  async function start() {
    cancelled.current = false;
    setState("working");
    setMessage("Starting the live comparison…");

    try {
      const response = await fetch(`${PUBLIC_API_URL}/api/v1/sync-all/start`, { method: "POST" });
      const data = await response.json() as { message?: string };
      if (!response.ok) throw new Error(data.message || "Could not start the comparison");

      const deadline = Date.now() + 5 * 60 * 1000;
      while (!cancelled.current && Date.now() < deadline) {
        await wait(3500);
        const sources = await readSources();
        const enabled = sources.filter((source) => source.enabled);
        const active = enabled.filter((source) => ACTIVE_STATES.has(source.last_sync_status));
        const failed = enabled.filter((source) => source.last_sync_status === "error");
        const finished = enabled.length - active.length;

        setMessage(
          active.length > 0
            ? `Checking Google Sheets: ${finished} of ${enabled.length} finished. ${active.length} still running.`
            : failed.length > 0
              ? `Comparison finished. ${failed.length} sheet${failed.length === 1 ? " has" : "s have"} an error; open Google Sheets to see the reason.`
              : `Comparison finished for all ${enabled.length} connected Google Sheets. Refreshing the results…`
        );

        if (active.length === 0) {
          setState(failed.length > 0 ? "error" : "done");
          await wait(1200);
          window.location.reload();
          return;
        }
      }

      setState("error");
      setMessage("The comparison is still running. You can continue using the app; refresh this page later to see the results.");
    } catch (error) {
      setState("error");
      setMessage(error instanceof Error ? error.message : "Could not start the comparison");
    }
  }

  return (
    <div className={`compare-now compare-${state}`}>
      <div>
        <strong>Compare with Google Sheets now</strong>
        <p>{message}</p>
      </div>
      <button className="button primary" type="button" onClick={start} disabled={state === "working"}>
        {state === "working" ? "Checking sheets…" : state === "done" ? "Comparison complete" : "Check for changes now"}
      </button>
    </div>
  );
}
