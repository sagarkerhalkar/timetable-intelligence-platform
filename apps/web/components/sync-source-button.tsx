"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { PUBLIC_API_URL, type SheetSource } from "@/lib/api";

const ACTIVE_STATUSES = new Set(["queued", "downloading", "analyzing"]);
const STATUS_LABELS: Record<string, string> = {
  queued: "Queued…",
  downloading: "Downloading sheet…",
  analyzing: "Understanding tabs and data…",
  success: "Live sync completed.",
  local_import: "Local import completed.",
  error: "Live sync failed."
};

function delay(milliseconds: number) {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
}

export function SyncSourceButton({ sourceId, disabled }: Readonly<{ sourceId: string; disabled?: boolean }>) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  async function sync() {
    setBusy(true);
    setMessage("Starting background sync…");
    try {
      const response = await fetch(`${PUBLIC_API_URL}/api/v1/sources/${sourceId}/sync/start`, {
        method: "POST"
      });
      const result = (await response.json()) as { status?: string; error?: string; detail?: string };
      if (!response.ok) {
        throw new Error(result.error ?? result.detail ?? "Live sync failed.");
      }

      for (let attempt = 0; attempt < 160; attempt += 1) {
        await delay(1500);
        const statusResponse = await fetch(`${PUBLIC_API_URL}/api/v1/sources/${sourceId}`, {
          cache: "no-store"
        });
        if (!statusResponse.ok) throw new Error("Could not read synchronization status.");
        const source = (await statusResponse.json()) as SheetSource;
        setMessage(STATUS_LABELS[source.last_sync_status] ?? source.last_sync_status);
        if (source.last_sync_status === "error") {
          throw new Error(source.last_error ?? "Live sync failed.");
        }
        if (!ACTIVE_STATUSES.has(source.last_sync_status)) {
          router.refresh();
          return;
        }
      }
      throw new Error("The scan is still running. You may leave this page and return later.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Live sync failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="sync-action">
      <button className="button secondary compact" type="button" onClick={sync} disabled={disabled || busy}>
        {busy ? "Checking…" : "Check now"}
      </button>
      <small role="status" aria-live="polite">{message}</small>
    </div>
  );
}
