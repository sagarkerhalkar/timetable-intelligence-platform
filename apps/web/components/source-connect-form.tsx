"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { PUBLIC_API_URL, type SheetSource } from "@/lib/api";

type ErrorPayload = { detail?: string; error?: string };
type SyncPayload = { status?: string; message?: string; detail?: string };

async function readPayload<T>(response: Response): Promise<T> {
  const text = await response.text();
  if (!text) return {} as T;
  try {
    return JSON.parse(text) as T;
  } catch {
    throw new Error(`The server returned an invalid response (${response.status}).`);
  }
}

export function SourceConnectForm() {
  const router = useRouter();
  const [status, setStatus] = useState<string>("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    // React's event.currentTarget is not guaranteed to remain available after await.
    // Capture the real form element before any asynchronous work.
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const name = String(form.get("name") ?? "").trim();
    const url = String(form.get("url") ?? "").trim();

    setBusy(true);
    setStatus("Saving connection…");

    try {
      const response = await fetch(`${PUBLIC_API_URL}/api/v1/sources`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, url, enabled: true }),
        signal: AbortSignal.timeout(20000)
      });

      const payload = await readPayload<SheetSource & ErrorPayload>(response);
      if (!response.ok) {
        throw new Error(payload.detail ?? payload.error ?? "The Google Sheet could not be connected.");
      }

      setStatus("Sheet saved. Starting background scan…");
      const syncResponse = await fetch(
        `${PUBLIC_API_URL}/api/v1/sources/${payload.id}/sync/start`,
        { method: "POST", signal: AbortSignal.timeout(20000) }
      );
      const syncPayload = await readPayload<SyncPayload>(syncResponse);
      if (!syncResponse.ok) {
        throw new Error(syncPayload.detail ?? "The sheet was saved, but the first scan could not start.");
      }

      formElement.reset();
      setStatus(syncPayload.message ?? "Sheet connected. Scanning continues in the background.");
      router.refresh();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Connection failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="source-form" onSubmit={submit}>
      <label>
        <span>Connection name</span>
        <input name="name" required minLength={2} maxLength={120} placeholder="Example: Class 12 Commerce" />
      </label>
      <label className="source-url-field">
        <span>Google Sheet link</span>
        <input name="url" type="url" required inputMode="url" placeholder="https://docs.google.com/spreadsheets/d/…" />
      </label>
      <button className="button primary" type="submit" disabled={busy}>
        {busy ? "Connecting…" : "Connect sheet"}
      </button>
      <p className="form-status" role="status" aria-live="polite">{status}</p>
    </form>
  );
}
