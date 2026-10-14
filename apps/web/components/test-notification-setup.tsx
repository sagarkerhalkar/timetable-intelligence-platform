"use client";

import type { ChangeEvent, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { PUBLIC_API_URL } from "@/lib/api";

export function TestNotificationSetup({ sourceId }: Readonly<{ sourceId: string }>) {
  const router = useRouter();
  const [channel, setChannel] = useState("whatsapp_personal");
  const [recipient, setRecipient] = useState("");
  const [appTime, setAppTime] = useState("18:00");
  const [resultTime, setResultTime] = useState("18:00");
  const [videoTime, setVideoTime] = useState("18:00");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!recipient.trim() && channel !== "google_chat") {
      setMessage("Enter the phone number, email address or Telegram chat ID.");
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      const response = await fetch(`${PUBLIC_API_URL}/api/v1/notification-presets/test-monitor`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          channel,
          recipient: recipient.trim() || "Google Chat webhook",
          source_id: sourceId,
          app_status_time: appTime,
          result_time: resultTime,
          video_time: videoTime
        })
      });
      if (!response.ok) {
        const body = await response.json().catch(() => null) as { detail?: string } | null;
        throw new Error(body?.detail ?? "Notification setup failed.");
      }
      setMessage("Four test notifications are active. Use Test now on the Notifications page to check delivery.");
      router.refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Notification setup failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="test-alert-setup" onSubmit={submit}>
      <div className="test-alert-intro">
        <p className="eyebrow">One simple setup</p>
        <h2>Turn on all test notifications</h2>
        <p>This creates four rules together: new-test alert, Saturday readiness, Monday Result Dashboard and Tuesday Video Solution. You can delete or change them later from Notifications.</p>
      </div>
      <label>
        <span>How should the message reach you?</span>
        <select value={channel} onChange={(event: ChangeEvent<HTMLSelectElement>) => setChannel(event.target.value)}>
          <option value="whatsapp_personal">Personal WhatsApp — open and press Send</option>
          <option value="email">Email — automatic after email setup</option>
          <option value="telegram">Telegram — automatic after bot setup</option>
          <option value="google_chat">Google Chat — automatic after webhook setup</option>
        </select>
      </label>
      <label>
        <span>{channel === "whatsapp_personal" ? "WhatsApp number with country code" : channel === "email" ? "Email address" : channel === "telegram" ? "Telegram chat ID" : "Recipient"}</span>
        <input
          value={recipient}
          onChange={(event) => setRecipient(event.target.value)}
          placeholder={channel === "whatsapp_personal" ? "+919876543210" : channel === "email" ? "name@example.com" : "Chat ID"}
          disabled={channel === "google_chat"}
        />
      </label>
      <div className="test-alert-times">
        <label><span>Saturday Sunday-test readiness</span><input type="time" value={appTime} onChange={(event) => setAppTime(event.target.value)} /></label>
        <label><span>Monday Result Dashboard</span><input type="time" value={resultTime} onChange={(event) => setResultTime(event.target.value)} /></label>
        <label><span>Tuesday Video Solution</span><input type="time" value={videoTime} onChange={(event) => setVideoTime(event.target.value)} /></label>
      </div>
      <div className="test-alert-plan">
        <span><b>Immediately after Sheet check</b> New test added</span>
        <span><b>Saturday {appTime}</b> Sunday-test App Status remaining</span>
        <span><b>Monday {resultTime}</b> Result Dashboard remaining</span>
        <span><b>Tuesday {videoTime}</b> Video Solution remaining</span>
      </div>
      <button className="button primary" disabled={busy} type="submit">{busy ? "Saving…" : "Activate all four alerts"}</button>
      {message ? <p className="form-message" role="status">{message}</p> : null}
      {channel === "whatsapp_personal" ? <small>Normal WhatsApp cannot send unattended. At the alert time, open Notifications and press Open WhatsApp, then Send.</small> : <small>Automatic delivery requires the selected channel to be configured on the server.</small>}
    </form>
  );
}
