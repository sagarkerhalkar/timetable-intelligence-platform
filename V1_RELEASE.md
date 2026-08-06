# v1 Windows LAN release

Current update package: `timetable-intelligence-platform-v1.0.10.2-powershell-parser-fix.zip`

SHA-256: `5c1f8ef7d64651472bbbe9baa5346219594a07e39679bf14680414ab3ee3ae87`

## v1.0.10.2 PowerShell parser repair

- Reapplies the complete v1.0.10 reliable hyperlink search, Google Sheet manager, Test Analysis, notification guidance and understandable Change History update.
- Fixes two Windows PowerShell parser errors caused by `$sourceName:` inside double-quoted strings. Both now use `${sourceName}:`.
- The earlier v1.0.10 attempt stopped during script parsing, before backup, service stop, application replacement, database changes or Sheet sync.
- All PowerShell files in the package were scanned for the same unsafe variable-colon pattern; no unsafe occurrences remain.
- The installer still requires backend tests, TypeScript validation, the complete Next.js production build, live sync for every enabled Sheet, YT Science Class 12 hyperlink validation, Test Analysis checks and page health checks before it reports success.
- Existing database, connected Google Sheets, notification rules and isolated ports remain preserved. Port 3457 remains protected.

The working LAN deployment remains `http://156.156.40.51:3500`.

The release package excludes credentials, recipients, logs, runtime files and backups.
