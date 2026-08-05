# v1 Windows LAN release

Current repair package: `timetable-intelligence-platform-v1.0.3-nirmaan-whatsapp-fix.zip`

SHA-256: `b2b01b9600b232474c9c2db6205ba54d04a400db2c498ee0c240fdfa0e48d5aa`

## v1.0.3 repairs

- The live Nirmaan Old NCERT timetable has one visually merged 6:00 PM heading across two subject columns. Both simultaneous classes are now retained instead of the second class overwriting the first.
- Live validation found 36 Nirmaan timetable entries: 12 New NCERT, 12 Old NCERT and 12 Nirmaan 2.0.
- The current Nirmaan workbook has 14 tabs and 795 searchable content-link occurrences; all 795 are indexed after the forced re-sync.
- Delete Rule remains visible on every notification schedule and removes that rule's delivery-test history after confirmation.
- Personal WhatsApp mode does not need a Business account. It opens WhatsApp Web/Desktop with a prefilled message and the user presses Send.
- Scheduled Personal WhatsApp items appear as Ready to send with an Open WhatsApp button.
- Fully automatic WhatsApp still requires an approved WhatsApp Business/provider API or webhook.

The working LAN deployment remains `http://156.156.40.51:3500`. Port 3457 remains protected.

The repair package excludes databases, credentials, Google Sheet data, recipients, logs, runtime files and backups.
