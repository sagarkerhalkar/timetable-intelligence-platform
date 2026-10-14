"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { PUBLIC_API_URL, type SheetSource } from "@/lib/api";

const OFFICIAL_SOURCES = [
  {
    name: "Commerce – Classes 11 & 12",
    url: "https://docs.google.com/spreadsheets/d/1vEGv2nzGYlFWtHT8SmvzGIYeL_Yl9RJNRohM2VHY0Lg/edit?gid=1456617162#gid=1456617162"
  },
  {
    name: "Science – Classes 11 & 12",
    url: "https://docs.google.com/spreadsheets/d/1j1yR4DRzqJwnkkfHmeWuv7vP-iDP0KZVahV4l9lcjEg/edit?gid=543178514#gid=543178514"
  },
  {
    name: "Humanities – Classes 11 & 12",
    url: "https://docs.google.com/spreadsheets/d/1M8mxrLzxZ9AixQ7fejbzIjhZGLgNzS7flMx6cXgiXHQ/edit?gid=1107684487#gid=1107684487"
  },
  {
    name: "Junior – Classes 7 & 8",
    url: "https://docs.google.com/spreadsheets/d/1a7qJpddbGL3fnR6RBmsrFxqjjVLB_g9Ryz7cQ1i0W8U/edit?gid=682067477#gid=682067477"
  }
] as const;

type ErrorPayload = { detail?: string; error?: string };
type SyncPayload = { detail?: string; message?: string };

async function readPayload<T>(response: Response): Promise<T> {
  const text = await response.text();
  if (!text) return {} as T;
  try {
    return JSON.parse(text) as T;
  } catch {
    throw new Error(`The server returned an invalid response (${response.status}).`);
  }
}

export function OfficialSourcesButton() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  async function connectOfficialSources() {
    setBusy(true);
    setMessage("Checking four official sheets…");
    try {
      for (const [index, source] of OFFICIAL_SOURCES.entries()) {
        setMessage(`Connecting ${index + 1} of ${OFFICIAL_SOURCES.length}: ${source.name}`);
        const response = await fetch(`${PUBLIC_API_URL}/api/v1/sources`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ ...source, enabled: true }),
          signal: AbortSignal.timeout(20000)
        });
        const payload = await readPayload<SheetSource & ErrorPayload>(response);
        if (!response.ok) {
          throw new Error(payload.detail ?? payload.error ?? `Could not connect ${source.name}.`);
        }

        const syncResponse = await fetch(
          `${PUBLIC_API_URL}/api/v1/sources/${payload.id}/sync/start`,
          { method: "POST", signal: AbortSignal.timeout(20000) }
        );
        const syncPayload = await readPayload<SyncPayload>(syncResponse);
        if (!syncResponse.ok) {
          throw new Error(syncPayload.detail ?? `Could not start ${source.name}.`);
        }
      }
      setMessage("All four sheets are connected. Scanning continues in the background.");
      router.refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "The official sheets could not be connected.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="official-source-actions">
      <button className="button primary" type="button" onClick={connectOfficialSources} disabled={busy}>
        {busy ? "Checking…" : "Connect / check all four sheets"}
      </button>
      <p className="form-status" role="status" aria-live="polite">{message}</p>
    </div>
  );
}
