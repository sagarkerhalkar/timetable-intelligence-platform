# v1.0.1 Weekly and Notification Repair

## Weekly timetable

The v1.0 weekly page requested 500 rows, while the API accepted a maximum of 100. FastAPI returned HTTP 422 and the web fallback displayed an empty timetable. v1.0.1 raises the verified timetable page limit to 1000 and requests the full week safely.

The selected weekly day now defaults to today when today has classes. Otherwise it automatically selects the first day in the week that has classes. Changing the stream also moves to a day that contains matching classes instead of leaving an empty panel.

## Notification rule deletion

A rule now has a Delete rule button. Deletion requires browser confirmation and removes both the rule and its delivery-test history.

## Channel setup

Run `D:\timetable-intelligence-platform\SETUP_NOTIFICATION_CHANNELS.cmd` on the server. It guides the administrator through Email, Google Chat, Telegram, WhatsApp provider webhook and Push webhook configuration, writes `.env.notifications`, and restarts only Timetable Intelligence.

Personal WhatsApp by itself cannot be used for automatic server delivery. A WhatsApp Business/API provider webhook is required.
