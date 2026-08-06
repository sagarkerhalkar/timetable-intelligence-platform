# v1.0.7 Test Monitor and Structured Search

## Purpose

This release treats **Test Series - 2026** as a structured test-operation workbook rather than a generic collection of links.

## Search

Search reads workbook name, tab, course, class, subject, chapter, topic, creator, file name, App Status, Test Date, Result Dashboard and Video Solution Update. Google Sheet and tab filters stay available when more sources are connected.

Romanised queries are indexed with the original Indic text. For example, `kabir` finds `कबीर के दोहे` in `Nirman 2026`.

## Test Monitor

The monitor shows:

- every structured test found in the workbook;
- App Status for `PRARAMBH 2026` and `Nirman 2026`;
- Result Dashboard for due tests in `PRARAMBH 2026`;
- Video Solution Update for due tests in `PRARAMBH 2026`;
- simple lists of remaining work without spreadsheet cell coordinates.

A test is due for Result Dashboard and Video Solution reporting only when its Test Date is marked done or is a date on/before today.

## Notification presets

One setup form creates four rules:

1. New test alert after each successful 30-minute Sheet check.
2. Sunday App Status report for `PRARAMBH 2026` and `Nirman 2026` (default 5:00 PM IST).
3. Monday Result Dashboard report for `PRARAMBH 2026` (default 5:00 PM IST).
4. Tuesday Video Solution report for `PRARAMBH 2026` (default 5:00 PM IST).

Personal WhatsApp prepares the message and requires the user to press Send. Email, Telegram and Google Chat can send automatically after their server credentials are configured.
