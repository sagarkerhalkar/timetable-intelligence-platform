"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { PUBLIC_API_URL } from "@/lib/api";

export function SourceDeleteButton({ sourceId, sourceName }: Readonly<{ sourceId: string; sourceName: string }>) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  async function remove() {
    const confirmed = window.confirm(
      `Remove “${sourceName}” from this app?\n\nThis removes only the local connection, search index and history. The Google Sheet itself will not be deleted.`
    );
    if (!confirmed) return;
    setBusy(true);
    setMessage("Removing local connection…");
    try {
      const response = await fetch(`${PUBLIC_API_URL}/api/v1/sources/${sourceId}`, {
        method: "DELETE",
        signal: AbortSignal.timeout(20000)
      });
      if (!response.ok) {
        const text = await response.text();
        throw new Error(text || "The connection could not be removed.");
      }
      setMessage("Removed.");
      router.refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Removal failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <span className="source-remove-wrap">
      <button className="button danger compact" type="button" onClick={remove} disabled={busy}>
        {busy ? "Removing…" : "Remove Sheet"}
      </button>
      {message ? <small role="status">{message}</small> : null}
    </span>
  );
}
