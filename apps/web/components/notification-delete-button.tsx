"use client";

import { useState } from "react";

export function NotificationDeleteButton({ ruleId, ruleName }: Readonly<{ ruleId: string; ruleName: string }>) {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  async function removeRule() {
    const confirmed = window.confirm(`Delete notification rule "${ruleName}"? Its delivery history will also be removed.`);
    if (!confirmed) return;

    setBusy(true);
    setMessage("Deleting…");
    try {
      const response = await fetch(`/backend/api/v1/notification-rules/${encodeURIComponent(ruleId)}`, {
        method: "DELETE"
      });
      if (!response.ok) {
        const detail = await response.text();
        throw new Error(detail || "The rule could not be deleted.");
      }
      setMessage("Deleted");
      window.setTimeout(() => window.location.reload(), 350);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Delete failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="notification-delete">
      <button className="button danger compact" type="button" disabled={busy} onClick={removeRule}>
        {busy ? "Deleting…" : "Delete rule"}
      </button>
      {message ? <small role="status">{message}</small> : null}
    </div>
  );
}
