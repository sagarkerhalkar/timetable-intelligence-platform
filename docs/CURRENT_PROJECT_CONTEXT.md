# Current Project Context — Timetable Intelligence Platform

This document is the short continuation source for a new ChatGPT/development session.

## Runtime

- Windows application root: `D:\\timetable-intelligence-platform`
- Web: port 3500
- API: port 3550
- Protected development port 3457 must never be modified by release installers.
- Public dynamic QR host is configured separately from the public repository.

## Timetable rules that must not regress

- Calendar-week calculations use India civil Monday-Sunday boundaries; never derive the weekday from a UTC-converted midnight.
- Today stream cards open the exact current date + stream timetable.
- Test Monitor maps Monday-Saturday source Test Dates to that same week's Sunday for readiness/counts while keeping the original source date visible; Sunday remains Sunday.
- Sheet Updates default to human grouped change stories; technical cell audit is secondary.
- Release installer backs up changed files/databases/build, runs all gates, and rolls back on any failure.

## QR Studio — locked product behavior

QR types:
- Calendar Event
- Contact/vCard
- Email
- Geo Location
- Phone
- URL
- Wi-Fi

Tracking:
- `tracked`: branded web scan experience + verified analytics.
- `direct`: native action payload; direct Wi-Fi is used for the normal OS Join Network flow and cannot provide equivalent web analytics.

Identity:
- Anonymous first-party device/browser identifier.
- Optional Identify with Email, requiring explicit scanner input.
- Do not claim silent Gmail or MAC-address collection.

Verified analytics:
- browser confirmation counts as a verified scan;
- link-preview/server fetches do not inflate primary scan KPIs;
- total verified scans and anonymous unique browser/devices are separate metrics;
- platform/source attribution is Exact when tagged, otherwise Detected/Unknown.

Device Intelligence:
- collect legitimate browser-exposed telemetry where available;
- unsupported optional fields must never block scanning;
- compact summaries in UI, deep technical telemetry expandable.

## v1.0.24 release candidate

Adds server-side reusable templates and Bulk Create.

Template stores:
- name/description;
- tracking and identity modes;
- QR design (logo, colors, dots, markers, frame, sizes);
- scan-screen experience (logo/full-screen image, colors, animation/settings);
- default flag.

Bulk Create:
- choose one tracked template;
- supply only `Name + URL` for each campaign;
- up to 500 rows per request;
- every QR gets a unique ID + slug and independent analytics;
- deleting a template never deletes already-created QR campaigns.

## Repository safety

Never commit:
- databases;
- credentials/secrets/tokens/cookies;
- recipient/member data;
- private Google Sheet contents;
- runtime logs;
- uploaded private/customer branding assets.

Stable branch stays `v1` until the real Windows installer accepts a release candidate.
