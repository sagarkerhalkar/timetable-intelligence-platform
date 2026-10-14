"use client";

import { ChangeEvent, FormEvent, useState } from "react";

function splitList(value: string): string[] {
  return value.split(/[,\n]/).map((item) => item.trim()).filter(Boolean);
}

const channelNotes: Record<string, string> = {
  whatsapp_personal: "No setup is required. At the selected time the app creates a Ready to send message. Open Notifications and press Open WhatsApp, then press Send.",
  email: "Automatic delivery. Configure SMTP once on the timetable server, then use Test now.",
  telegram: "Automatic delivery. Add a Telegram bot token on the server and enter the target chat ID.",
  google_chat: "Automatic delivery. Add the Google Chat space webhook on the server.",
  whatsapp: "Automatic WhatsApp requires an approved WhatsApp Business/provider API.",
  push: "Automatic delivery through your own push webhook service."
};

export function NotificationRuleForm() {
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const [eventType, setEventType] = useState("daily_timetable");
  const [channel, setChannel] = useState("whatsapp_personal");
  const [whatsappMode, setWhatsappMode] = useState("person");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    setBusy(true);
    setStatus("Saving rule…");
    try {
      const minutesValue = String(data.get("minutes_before") ?? "");
      const timeValue = String(data.get("send_time") ?? "");
      let recipients = splitList(String(data.get("recipients") ?? ""));
      if (channel === "whatsapp_personal" && whatsappMode === "choose") recipients = ["choose_in_whatsapp"];
      const payload = {
        id: crypto.randomUUID(),
        name: String(data.get("name") ?? "Daily timetable"),
        enabled: true,
        event_type: eventType,
        send_time: eventType === "before_class" ? null : (timeValue || "07:00"),
        weekday: eventType === "weekly_timetable" ? Number(data.get("weekday") ?? 0) : null,
        minutes_before: eventType === "before_class" && minutesValue ? Number(minutesValue) : null,
        timezone: "Asia/Kolkata",
        channels: [channel],
        recipients,
        streams: splitList(String(data.get("streams") ?? "")),
        classes: splitList(String(data.get("classes") ?? "")),
        subjects: splitList(String(data.get("subjects") ?? "")),
        include_pdf: data.get("include_pdf") === "on",
        include_excel: data.get("include_excel") === "on",
        created_at: new Date().toISOString()
      };
      if (!recipients.length && channel !== "google_chat") throw new Error("Add at least one recipient.");
      if (channel === "whatsapp_personal" && whatsappMode === "person") {
        const invalid = recipients.find((item) => item.replace(/\D/g, "").length < 10);
        if (invalid) throw new Error("Enter the WhatsApp number with country code, for example +919876543210.");
      }
      const response = await fetch("/backend/api/v1/notification-rules", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (!response.ok) throw new Error((await response.text()) || "The rule could not be saved.");
      setStatus(channel === "whatsapp_personal"
        ? "Rule saved. Press Open WhatsApp test on the saved rule."
        : "Rule saved. Press Test now to verify automatic delivery.");
      window.setTimeout(() => window.location.reload(), 900);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "The rule could not be saved.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="notification-form notification-simple-form" onSubmit={submit}>
      <section className="notification-step-card">
        <div className="notification-step-number">1</div>
        <div className="notification-step-fields">
          <h3>What should be sent?</h3>
          <label><span>Notification</span><select name="event_type" value={eventType} onChange={(event: ChangeEvent<HTMLSelectElement>) => setEventType(event.target.value)}><option value="daily_timetable">Today&apos;s timetable every day</option><option value="weekly_timetable">Complete weekly timetable</option><option value="before_class">Reminder before each class</option><option value="timetable_not_updated">Warning when timetable is not updated</option></select></label>
          <label><span>Rule name</span><input name="name" required minLength={2} defaultValue="Daily timetable" /></label>
        </div>
      </section>

      <section className="notification-step-card">
        <div className="notification-step-number">2</div>
        <div className="notification-step-fields">
          <h3>When should it be ready?</h3>
          {eventType === "before_class" ? (
            <label><span>Reminder time</span><select name="minutes_before" defaultValue="30"><option value="10">10 minutes before</option><option value="15">15 minutes before</option><option value="30">30 minutes before</option><option value="60">1 hour before</option><option value="1440">1 day before</option></select></label>
          ) : (
            <label><span>Time in IST</span><input name="send_time" type="time" defaultValue={eventType === "weekly_timetable" ? "08:00" : "07:00"} required /></label>
          )}
          {eventType === "weekly_timetable" ? <label><span>Day</span><select name="weekday" defaultValue="0"><option value="0">Monday</option><option value="1">Tuesday</option><option value="2">Wednesday</option><option value="3">Thursday</option><option value="4">Friday</option><option value="5">Saturday</option><option value="6">Sunday</option></select></label> : null}
        </div>
      </section>

      <section className="notification-step-card recommended-channel-card">
        <div className="notification-step-number">3</div>
        <div className="notification-step-fields">
          <h3>How should it be delivered?</h3>
          <label><span>Channel</span><select name="channel" value={channel} onChange={(event: ChangeEvent<HTMLSelectElement>) => setChannel(event.target.value)}><option value="whatsapp_personal">Personal WhatsApp — no Business account</option><option value="email">Email — automatic</option><option value="telegram">Telegram — automatic</option><option value="google_chat">Google Chat — automatic</option><option value="whatsapp">WhatsApp Business/provider — automatic</option><option value="push">Push webhook — automatic</option></select></label>
          {channel === "whatsapp_personal" ? <label><span>Who should receive it?</span><select value={whatsappMode} onChange={(event: ChangeEvent<HTMLSelectElement>) => setWhatsappMode(event.target.value)}><option value="person">One fixed person</option><option value="choose">Choose person or group when WhatsApp opens</option></select></label> : null}
          {channel === "google_chat" ? <div className="recipient-help-box"><strong>Recipient comes from the Google Chat webhook.</strong><span>Configure one webhook for the Space/group. Leave recipient blank.</span></div> : (
            <label><span>{channel === "whatsapp_personal" ? "WhatsApp number" : channel === "telegram" ? "Telegram person/group chat ID" : channel === "email" ? "Email address(es)" : "Recipient"}</span><textarea name="recipients" disabled={channel === "whatsapp_personal" && whatsappMode === "choose"} placeholder={channel === "whatsapp_personal" ? (whatsappMode === "choose" ? "You will choose inside WhatsApp" : "+919876543210") : channel === "telegram" ? "Person: 123456789 or group: -1001234567890" : channel === "email" ? "teacher@example.com, admin@example.com" : "Channel recipient"} /></label>
          )}
          <p className="channel-explanation"><strong>{channel === "whatsapp_personal" ? "Works with your normal WhatsApp." : "Automatic channel."}</strong> {channelNotes[channel]}</p>
        </div>
      </section>

      <details className="notification-advanced-options">
        <summary>Optional filters and attachments</summary>
        <div className="notification-advanced-grid">
          <label><span>Streams</span><input name="streams" placeholder="Commerce, Science" /></label>
          <label><span>Classes</span><input name="classes" placeholder="Class 8, Class 12" /></label>
          <label><span>Subjects</span><input name="subjects" placeholder="Mathematics, Economics" /></label>
          <div className="attachment-options"><label><input type="checkbox" name="include_pdf" /> Include PDF</label><label><input type="checkbox" name="include_excel" /> Include Excel</label></div>
        </div>
      </details>

      <div className="notification-submit"><button className="button primary" type="submit" disabled={busy}>{busy ? "Saving…" : "Save notification"}</button><p className="form-status" role="status">{status}</p></div>
    </form>
  );
}
