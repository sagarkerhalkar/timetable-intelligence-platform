"use client";

import { useState } from "react";
import type { NotificationTestResponse } from "@/lib/types";

function whatsappUrl(recipient: string, message: string): string {
  let digits = recipient.replace(/\D/g, "");
  if (digits.length === 10) digits = `91${digits}`;
  return `https://wa.me/${digits}?text=${encodeURIComponent(message)}`;
}

type Props = Readonly<{
  ruleId: string;
  channels?: string[];
  recipients?: string[];
}>;

export function NotificationTestButton({ ruleId, channels = [], recipients = [] }: Props) {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [tone, setTone] = useState("neutral");

  async function test() {
    const isPersonalWhatsApp = channels.includes("whatsapp_personal");
    const popup = isPersonalWhatsApp ? window.open("about:blank", "_blank") : null;
    setBusy(true);
    setTone("neutral");
    setMessage(isPersonalWhatsApp ? "Preparing WhatsApp message…" : "Sending test…");
    try {
      const response = await fetch(`/backend/api/v1/notification-rules/${encodeURIComponent(ruleId)}/test`, { method: "POST" });
      const data = await response.json() as NotificationTestResponse & { detail?: string };
      if (!response.ok) throw new Error(data.detail || "Test failed.");
      const sent = data.deliveries.filter((item) => item.status === "sent").length;
      const actionRequired = data.deliveries.filter((item) => item.status === "action_required").length;
      const notConfigured = data.deliveries.filter((item) => item.status === "not_configured").length;
      const failed = data.deliveries.filter((item) => item.status === "failed").length;
      if (actionRequired && isPersonalWhatsApp) {
        const recipient = recipients[0] ?? "";
        if (!recipient) throw new Error("Add a WhatsApp phone number to this rule first.");
        const target = whatsappUrl(recipient, data.preview);
        if (popup) popup.location.href = target;
        else window.location.href = target;
        setTone("good");
        setMessage("WhatsApp opened with the message ready. Press Send in WhatsApp.");
      } else if (sent) {
        if (popup) popup.close();
        setTone("good");
        setMessage(`${sent} test notification${sent === 1 ? "" : "s"} delivered.`);
      } else if (notConfigured) {
        if (popup) popup.close();
        setTone("warning");
        setMessage("Scheduler works, but this automatic channel is not configured on the server yet.");
      } else if (failed) {
        if (popup) popup.close();
        setTone("bad");
        setMessage(data.deliveries.find((item) => item.error)?.error || "Delivery failed.");
      } else {
        if (popup) popup.close();
        setTone("warning");
        setMessage("Test completed without a configured recipient.");
      }
    } catch (error) {
      if (popup) popup.close();
      setTone("bad");
      setMessage(error instanceof Error ? error.message : "Test failed.");
    } finally {
      setBusy(false);
    }
  }

  return <div className={`notification-test notification-test-${tone}`}><button className="button secondary compact" type="button" disabled={busy} onClick={test}>{busy ? "Testing…" : channels.includes("whatsapp_personal") ? "Open WhatsApp test" : "Test now"}</button>{message ? <small role="status">{message}</small> : null}</div>;
}
