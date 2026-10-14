import { NotificationDeleteButton } from "@/components/notification-delete-button";
import { NotificationRuleForm } from "@/components/notification-rule-form";
import { NotificationTestButton } from "@/components/notification-test-button";
import { PageAutoRefresh } from "@/components/page-auto-refresh";
import { PersonalWhatsAppButton } from "@/components/personal-whatsapp-button";
import { formatDateTime } from "@/lib/format";
import { getNotificationDeliveries, getNotificationRules, getNotificationStatus } from "@/lib/api";

export const metadata = { title: "Notifications" };

const weekdayNames = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

function eventLabel(value: string): string {
  const labels: Record<string, string> = {
    daily_timetable: "Daily timetable",
    weekly_timetable: "Weekly timetable",
    before_class: "Before a class",
    timetable_not_updated: "Timetable not updated",
    new_test_added: "New test added",
    test_app_status: "Saturday Sunday-test readiness",
    test_result_dashboard: "Monday Result Dashboard",
    test_video_solution: "Tuesday Video Solution"
  };
  return labels[value] ?? value.replaceAll("_", " ");
}

function scheduleLabel(rule: Awaited<ReturnType<typeof getNotificationRules>>[number]): string {
  if (rule.event_type === "before_class") return `${rule.minutes_before ?? 0} minutes before every matching class`;
  if (rule.event_type === "new_test_added") return "After every successful 30-minute Google Sheet check";
  const time = rule.send_time ?? "No time selected";
  if (["weekly_timetable", "test_app_status", "test_result_dashboard", "test_video_solution"].includes(rule.event_type)) return `${weekdayNames[rule.weekday ?? 0] ?? "Monday"} at ${time} IST`;
  return `Every day at ${time} IST`;
}

function channelReady(value: boolean | undefined): string {
  return value ? "Configured and ready" : "Setup required";
}

function recipientLabel(value: string): string {
  return value === "choose_in_whatsapp" ? "Choose person/group in WhatsApp" : value;
}

export default async function NotificationsPage() {
  const [rules, status, deliveries] = await Promise.all([
    getNotificationRules(), getNotificationStatus(), getNotificationDeliveries()
  ]);
  const active = rules.filter((rule) => rule.enabled).length;

  return (
    <>
      <PageAutoRefresh minutes={5} />
      <section className="notification-command-v1">
        <div><p className="eyebrow">Simple timetable reminders</p><h1>Notifications</h1><p>For your normal WhatsApp account, choose Personal WhatsApp. No Business account or API setup is required.</p></div>
        <div className="notification-command-stats"><span><strong>{active}</strong> active rules</span><span><strong>{status.scheduler_active ? "ON" : "OFF"}</strong> scheduler</span><span><strong>{status.sheet_refresh_minutes}m</strong> sheet refresh</span></div>
      </section>

      <section className="personal-whatsapp-simple-guide">
        <div className="guide-title"><span>✓</span><div><strong>Recommended for you: Personal WhatsApp</strong><p>It works with your existing normal WhatsApp account.</p></div></div>
        <div className="three-simple-steps"><article><b>1</b><span>Add phone number</span><small>Example: +919876543210</small></article><article><b>2</b><span>Choose day and time</span><small>The scheduler prepares the message.</small></article><article><b>3</b><span>Open WhatsApp and Send</span><small>Personal WhatsApp cannot auto-press Send.</small></article></div>
      </section>

      <section className="notification-message-example-v105">
        <div><p className="eyebrow">Easy message format</p><h2>Every class will show the complete path</h2><p>The stream, class, batch, subject and lesson are kept on separate readable lines.</p></div>
        <div className="notification-phone-preview">
          <strong>5:00 PM</strong>
          <span>Humanities → Class 11 → Prarambh → Political Science</span>
          <b>Election and Representation (L3) - Political Science</b>
          <hr />
          <strong>6:00 PM</strong>
          <span>Nirmaan → Class 8 → Old NCERT → Mathematics</span>
          <b>Mensuration L1</b>
        </div>
      </section>

      <section className="notification-channel-dashboard panel">
        <div className="panel-title"><div><p className="eyebrow">Step 1 — choose delivery type</p><h2>Where will the notification go?</h2><p>Person and group delivery work differently. Choose the card that matches your need.</p></div></div>
        <div className="notification-channel-grid">
          <article className="channel-ready-card"><div><span>💬</span><b>Personal WhatsApp</b><em>Ready</em></div><p><strong>One person:</strong> enter the mobile number.<br /><strong>Any person or group:</strong> choose “Select inside WhatsApp” and pick the contact/group when WhatsApp opens.</p><small>Normal WhatsApp works. You press the final Send button.</small></article>
          <article className={status.configured_channels.telegram ? "channel-ready-card" : "channel-setup-card"}><div><span>✈️</span><b>Telegram</b><em>{channelReady(status.configured_channels.telegram)}</em></div><p><strong>Person:</strong> use that person&apos;s chat ID.<br /><strong>Group:</strong> add the bot to the group and use the group chat ID, commonly starting with <code>-100</code>.</p><small>Automatic after the bot token is configured.</small></article>
          <article className={status.configured_channels.google_chat ? "channel-ready-card" : "channel-setup-card"}><div><span>👥</span><b>Google Chat Space</b><em>{channelReady(status.configured_channels.google_chat)}</em></div><p>One webhook belongs to one Google Chat Space. Everyone in that Space receives the notification. No recipient is entered in the rule.</p><small>Best for a teacher/admin group.</small></article>
          <article className={status.configured_channels.email ? "channel-ready-card" : "channel-setup-card"}><div><span>✉️</span><b>Email</b><em>{channelReady(status.configured_channels.email)}</em></div><p>Enter one or many email addresses separated by commas. Each address receives the message automatically.</p><small>SMTP setup is required once.</small></article>
        </div>
        <div className="notification-server-setup">
          <div><strong>Configure Email, Telegram or Google Chat on the timetable server</strong><p>Double-click the setup file below. Choose the channel, enter its token/webhook, save, then return here and press Test now.</p></div>
          <code>D:\timetable-intelligence-platform\SETUP_NOTIFICATION_CHANNELS.cmd</code>
          <ol><li>Telegram: create a bot with <b>@BotFather</b>, copy the bot token, then enter person/group chat ID in the rule.</li><li>Google Chat: open the Space → Apps & integrations → Webhooks → create webhook → paste the webhook in the setup tool.</li><li>Email: choose Gmail, Microsoft 365 or custom SMTP and use an app password where required.</li></ol>
        </div>
      </section>

      <section className="test-alert-link"><div><span>✓</span><div><strong>Need test completion alerts?</strong><p>Create New Test, Saturday 6 PM Sunday-test readiness, Monday 6 PM Result Dashboard and Tuesday 6 PM Video Solution alerts together.</p></div></div><a className="button primary" href="/tests">Open Test Monitor</a></section>

      <details className="notification-builder-v1" open={!rules.length}><summary>+ Create a notification</summary><div className="panel"><NotificationRuleForm /></div></details>

      <section className="panel notification-rules-v1">
        <div className="panel-title"><div><p className="eyebrow">Saved schedules</p><h2>Your notification rules</h2></div><span className="status-pill neutral">{rules.length} total</span></div>
        {rules.length ? <div className="notification-rule-list-v1">{rules.map((rule) => (
          <article key={rule.id}>
            <div className="rule-time-v1"><span>{rule.event_type === "before_class" ? "−" : rule.send_time?.slice(0, 2) ?? "--"}</span><small>{rule.event_type === "before_class" ? `${rule.minutes_before ?? 0} min` : rule.send_time?.slice(3) ?? "--"}</small></div>
            <div className="rule-body-v1"><div className="friendly-meta"><span className={`status-pill ${rule.enabled ? "good" : "neutral"}`}>{rule.enabled ? "Active" : "Paused"}</span><span>{eventLabel(rule.event_type)}</span></div><h3>{rule.name}</h3><p className="rule-schedule-copy">⏰ {scheduleLabel(rule)}</p><p>{rule.channels.map((item) => item === "whatsapp_personal" ? "Personal WhatsApp" : item.replaceAll("_", " ")).join(", ")} · {rule.recipients.map(recipientLabel).join(", ") || "No recipient"}</p><small>Filters: {[...rule.streams, ...rule.classes, ...rule.subjects].join(", ") || "All classes"}</small></div>
            <div className="rule-actions-v1"><NotificationTestButton ruleId={rule.id} channels={rule.channels} recipients={rule.recipients} /><NotificationDeleteButton ruleId={rule.id} ruleName={rule.name} /></div>
          </article>
        ))}</div> : <div className="empty-state compact-empty"><span>🔔</span><h2>No notification yet</h2><p>Click Create a notification. Personal WhatsApp is already selected.</p></div>}
      </section>

      <section className="panel delivery-history-v1">
        <div className="panel-title"><div><p className="eyebrow">Ready and sent messages</p><h2>Notification history</h2></div></div>
        {deliveries.length ? <div className="delivery-list-v1">{deliveries.slice(0, 12).map((item) => <article key={item.id}><span className={`delivery-dot delivery-${item.status}`} /><div><strong>{item.rule_name}</strong><small>{item.channel === "whatsapp_personal" ? "Personal WhatsApp" : item.channel.replaceAll("_", " ")} → {recipientLabel(item.recipient)}</small>{item.error ? <small className="error-copy">{item.error}</small> : null}{item.status === "action_required" && item.channel === "whatsapp_personal" ? <PersonalWhatsAppButton recipient={item.recipient} message={item.message} /> : null}</div><div><span>{item.status === "action_required" ? "Ready to send" : item.is_test ? "Test" : item.status}</span><time>{formatDateTime(item.attempted_at)}</time></div></article>)}</div> : <div className="changes-clear-state"><span>○</span><h2>No message prepared yet</h2><p>Save a rule and press the test button. The result appears here.</p></div>}
      </section>

      <details className="advanced-channel-setup"><summary>WhatsApp Business/provider and push webhook (advanced)</summary><div><p>Fully unattended WhatsApp requires an approved Business/provider API. Push requires your own webhook service. Personal WhatsApp above is the safe option without a Business account.</p></div></details>
    </>
  );
}
