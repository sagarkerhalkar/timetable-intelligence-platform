from __future__ import annotations

import asyncio
import json
import smtplib
import ssl
from datetime import UTC, date, datetime, time, timedelta
from email.message import EmailMessage
from typing import Iterable
from uuid import uuid4

import httpx

from ..config import settings
from ..database import Database
from ..models import NotificationDelivery, NotificationRule, TestRecord, TimetableEntry
from ..timezones import INDIA_TIMEZONE
from .test_series import status_is_done, test_is_due, tests_for_sunday, weekly_cycle


def _matches(value: str | None, filters: Iterable[str]) -> bool:
    wanted = [item.casefold().strip() for item in filters if item.strip()]
    if not wanted:
        return True
    candidate = (value or "").casefold()
    return any(item in candidate for item in wanted)


def _rule_entries(database: Database, rule: NotificationRule, target_date: date) -> list[TimetableEntry]:
    return [
        item
        for item in database.list_timetable()
        if item.class_date == target_date
        and _matches(item.stream, rule.streams)
        and _matches(item.class_name, rule.classes)
        and _matches(item.subject, rule.subjects)
    ]


def _clean_path_part(value: str | None) -> str | None:
    text = (value or "").strip()
    return text or None


def _display_batch(entry: TimetableEntry) -> str | None:
    batch = _clean_path_part(entry.batch)
    stream = _clean_path_part(entry.stream)
    if not batch:
        return None
    # Avoid repeating the stream in paths such as
    # Nirmaan -> Class 8 -> Nirmaan Old NCERT.
    if stream and batch.casefold().startswith(stream.casefold() + " "):
        batch = batch[len(stream):].strip(" -–|>")
    replacements = {
        "nirmaan old ncert": "Old NCERT",
        "nirmaan new ncert": "New NCERT",
        "nirmaan 2.0": "Nirmaan 2.0",
        "nirmaan 2.o": "Nirmaan 2.0",
        "prarambh + prarambh pro": "Prarambh + Pro",
    }
    return replacements.get(batch.casefold(), batch)


def _entry_path(entry: TimetableEntry) -> str:
    parts = [
        _clean_path_part(entry.stream),
        _clean_path_part(entry.class_name),
        _display_batch(entry),
        _clean_path_part(entry.subject),
    ]
    unique: list[str] = []
    for part in parts:
        if part and not any(part.casefold() == existing.casefold() for existing in unique):
            unique.append(part)
    return " → ".join(unique) or "Class details pending"


def _entry_message_lines(entry: TimetableEntry, *, include_date: bool = False) -> list[str]:
    start = entry.start_time.strftime("%I:%M %p").lstrip("0") if entry.start_time else "Time pending"
    first = f"{entry.class_date:%a %d %b} · {start}" if include_date and entry.class_date else start
    topic = _clean_path_part(entry.topic) or "Lesson topic not added"
    return [first, _entry_path(entry), topic]



def _rule_test_records(database: Database, rule: NotificationRule) -> list[TestRecord]:
    records = database.list_test_records()
    if rule.source_ids:
        records = [item for item in records if item.source_id in rule.source_ids]
    if rule.sheet_names:
        wanted = {item.casefold() for item in rule.sheet_names}
        records = [item for item in records if item.sheet_name.casefold() in wanted]
    if rule.classes:
        records = [item for item in records if _matches(item.class_name, rule.classes)]
    if rule.subjects:
        records = [item for item in records if _matches(item.subject, rule.subjects)]
    return records


def _test_path(record: TestRecord) -> str:
    parts = [record.sheet_name, record.course, record.class_name, record.subject]
    unique: list[str] = []
    for value in parts:
        text = (value or "").strip()
        if text and not any(text.casefold() == existing.casefold() for existing in unique):
            unique.append(text)
    return " → ".join(unique)


def _test_title(record: TestRecord) -> str:
    return (
        record.topic
        or record.document_title
        or record.pdf_title
        or record.chapter_number
        or "Test name not added"
    )


def _event_cycle_records(records: list[TestRecord], event_type: str) -> tuple[list[TestRecord], date | None]:
    now = datetime.now(INDIA_TIMEZONE)
    if event_type == "test_app_status":
        _, _, sunday, _, _ = weekly_cycle(now)
        return tests_for_sunday(records, sunday), sunday
    # Monday and Tuesday reports belong to the most recent Sunday test cycle.
    days_since_sunday = (now.weekday() + 1) % 7
    sunday = now.date() - timedelta(days=days_since_sunday)
    selected = tests_for_sunday(records, sunday)
    # Older/baseline rows may not have an exact first-seen time. Keep the Test
    # button useful by falling back to already-due records when no cycle match
    # can be calculated. Scheduled weekly runs still prefer the exact Sunday.
    if not selected:
        selected = [item for item in records if test_is_due(item, now.date())]
    return selected, sunday


def _status_report(
    records: list[TestRecord],
    *,
    field: str,
    heading: str,
    is_test: bool = False,
) -> str:
    eligible = records
    done = [item for item in eligible if status_is_done(getattr(item, field))]
    pending = [item for item in eligible if not status_is_done(getattr(item, field))]
    prefix = "TEST - " if is_test else ""
    lines = [
        f"{prefix}{heading}",
        f"Checked: {len(eligible)} tests | Done: {len(done)} | Remaining: {len(pending)}",
    ]
    if not eligible:
        lines.append("No eligible tests were found for this report.")
        return "\n".join(lines)
    if not pending:
        lines.append("Everything is complete. No action is pending.")
        return "\n".join(lines)
    lines.append("")
    lines.append("Remaining work:")
    for index, item in enumerate(pending[:25], start=1):
        value = (getattr(item, field) or "Blank").strip()
        lines.append(f"{index}. {_test_path(item)}")
        lines.append(f"   {_test_title(item)}")
        lines.append(f"   Current status: {value}")
    if len(pending) > 25:
        lines.append(f"+ {len(pending) - 25} more pending tests. Open Test Monitor for the complete list.")
    return "\n".join(lines)


def build_test_notification_message(
    database: Database,
    rule: NotificationRule,
    *,
    is_test: bool = False,
    new_records: list[TestRecord] | None = None,
) -> str:
    records = new_records if new_records is not None else _rule_test_records(database, rule)
    if rule.event_type == "new_test_added":
        prefix = "TEST - " if is_test else ""
        if not records:
            return f"{prefix}New test alert\nNo new test is waiting right now. The alert will run after each 30-minute Sheet check."
        lines = [f"{prefix}{len(records)} new test{'s' if len(records) != 1 else ''} added"]
        for index, item in enumerate(records[:15], start=1):
            lines.extend([
                "",
                f"{index}. {_test_path(item)}",
                _test_title(item),
                f"App status: {item.app_status or 'Not updated'}",
            ])
        if len(records) > 15:
            lines.append(f"\n+ {len(records) - 15} more new tests. Open Test Monitor.")
        return "\n".join(lines)
    if rule.event_type in {"test_app_status", "test_result_dashboard", "test_video_solution"}:
        cycle_records, sunday = _event_cycle_records(records, rule.event_type)
        sunday_text = sunday.strftime("%d %b %Y") if sunday else "the Sunday test"
        if rule.event_type == "test_app_status":
            heading = f"Sunday test readiness for {sunday_text} — Saturday 6:00 PM check"
            return _status_report(cycle_records, field="app_status", heading=heading, is_test=is_test)
        if rule.event_type == "test_result_dashboard":
            heading = f"Monday Result Dashboard report — Sunday {sunday_text} — due 6:00 PM"
            return _status_report(cycle_records, field="result_dashboard", heading=heading, is_test=is_test)
        heading = f"Tuesday Video Solution report — Sunday {sunday_text} — due 6:00 PM"
        return _status_report(cycle_records, field="video_solution_update", heading=heading, is_test=is_test)
    return "Test monitor rule is not supported."

def build_notification_message(
    database: Database,
    rule: NotificationRule,
    *,
    is_test: bool = False,
    target_date: date | None = None,
    class_entry: TimetableEntry | None = None,
) -> str:
    now = datetime.now(INDIA_TIMEZONE)
    target = target_date or now.date()
    if rule.event_type in {"new_test_added", "test_app_status", "test_result_dashboard", "test_video_solution"}:
        return build_test_notification_message(database, rule, is_test=is_test)
    prefix = "TEST - " if is_test else ""
    if class_entry is not None:
        return "\n".join([f"{prefix}Class reminder", *_entry_message_lines(class_entry)])

    entries = _rule_entries(database, rule, target)
    if rule.event_type == "weekly_timetable":
        end = target + timedelta(days=6)
        week_entries = [
            item for item in database.list_timetable()
            if item.class_date and target <= item.class_date <= end
            and _matches(item.stream, rule.streams)
            and _matches(item.class_name, rule.classes)
            and _matches(item.subject, rule.subjects)
        ]
        if not week_entries:
            return f"{prefix}Weekly timetable ({target:%d %b} - {end:%d %b %Y})\nNo verified classes found for this week."
        lines = [f"{prefix}Weekly timetable ({target:%d %b} - {end:%d %b %Y})"]
        current_day: date | None = None
        for item in week_entries[:70]:
            if item.class_date != current_day:
                current_day = item.class_date
                lines.append("")
                lines.append(current_day.strftime("%A, %d %B"))
            detail = _entry_message_lines(item)
            lines.append(f"{detail[0]} | {detail[1]}")
            lines.append(f"Lesson: {detail[2]}")
        if len(week_entries) > 70:
            lines.append(f"\n+ {len(week_entries) - 70} more classes. Open the app for the complete week.")
        return "\n".join(lines)

    if rule.event_type == "timetable_not_updated":
        return (
            f"{prefix}Timetable update check for {target:%A, %d %B %Y}\n"
            + (f"{len(entries)} verified classes are available." if entries else "No verified timetable is available yet.")
        )

    if not entries:
        return f"{prefix}Daily timetable - {target:%A, %d %B %Y}\nNo verified classes found for this date."
    lines = [f"{prefix}Daily timetable - {target:%A, %d %B %Y}"]
    for index, item in enumerate(entries[:40], start=1):
        detail = _entry_message_lines(item)
        lines.extend(["", f"{index}. {detail[0]}", detail[1], detail[2]])
    if len(entries) > 40:
        lines.append(f"\n+ {len(entries) - 40} more classes. Open the app for the complete timetable.")
    return "\n".join(lines)


class NotificationService:
    def __init__(self, database: Database) -> None:
        self.database = database

    def configured_channels(self) -> dict[str, bool]:
        return {
            "email": bool(settings.smtp_host and settings.smtp_from),
            "google_chat": bool(settings.google_chat_webhook_url),
            "telegram": bool(settings.telegram_bot_token),
            "whatsapp_personal": True,
            "whatsapp": bool(settings.whatsapp_webhook_url),
            "push": bool(settings.push_webhook_url),
        }

    async def test_rule(self, rule: NotificationRule) -> tuple[str, list[NotificationDelivery]]:
        preview = build_notification_message(self.database, rule, is_test=True)
        deliveries = await self._deliver(rule, preview, is_test=True, scheduled_for=None)
        return preview, deliveries

    async def send_scheduled(
        self,
        rule: NotificationRule,
        message: str,
        scheduled_for: datetime,
        dedupe_suffix: str,
    ) -> list[NotificationDelivery]:
        return await self._deliver(
            rule,
            message,
            is_test=False,
            scheduled_for=scheduled_for,
            dedupe_suffix=dedupe_suffix,
        )

    async def _deliver(
        self,
        rule: NotificationRule,
        message: str,
        *,
        is_test: bool,
        scheduled_for: datetime | None,
        dedupe_suffix: str | None = None,
    ) -> list[NotificationDelivery]:
        channels = rule.channels or ["email"]
        results: list[NotificationDelivery] = []
        for channel in channels:
            recipients = rule.recipients or ["No recipient"]
            if channel == "google_chat":
                recipients = ["Google Chat webhook"]
            for recipient in recipients:
                base_key = dedupe_suffix or f"test:{datetime.now(UTC).isoformat()}:{uuid4()}"
                dedupe_key = f"{rule.id}:{channel}:{recipient}:{base_key}"
                if not is_test and self.database.notification_delivery_exists(dedupe_key):
                    continue
                status, error = await self._send_channel(channel, recipient, message)
                attempted = datetime.now(UTC)
                delivery = NotificationDelivery(
                    id=str(uuid4()),
                    rule_id=rule.id,
                    rule_name=rule.name,
                    channel=channel,
                    recipient=recipient,
                    status=status,
                    message=message,
                    error=error,
                    attempted_at=attempted,
                    scheduled_for=scheduled_for,
                    is_test=is_test,
                    dedupe_key=dedupe_key,
                )
                self.database.insert_notification_delivery(delivery)
                results.append(delivery)
        return results

    async def _send_channel(self, channel: str, recipient: str, message: str) -> tuple[str, str | None]:
        if channel == "whatsapp_personal":
            # Personal WhatsApp has no supported unattended server API. The UI
            # opens WhatsApp Web/Desktop with a prefilled message and the user
            # performs the final Send tap. Scheduled rules remain visible in
            # Delivery History as action-required items.
            return "action_required", None
        configured = self.configured_channels()
        if not configured.get(channel, False):
            return "not_configured", f"{channel.replace('_', ' ').title()} is not configured on the server."
        try:
            if channel == "email":
                await asyncio.to_thread(self._send_email, recipient, message)
            elif channel == "google_chat":
                async with httpx.AsyncClient(timeout=20) as client:
                    response = await client.post(settings.google_chat_webhook_url, json={"text": message})
                    response.raise_for_status()
            elif channel == "telegram":
                url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
                async with httpx.AsyncClient(timeout=20) as client:
                    response = await client.post(url, json={"chat_id": recipient, "text": message})
                    response.raise_for_status()
            elif channel == "whatsapp":
                async with httpx.AsyncClient(timeout=20) as client:
                    response = await client.post(
                        settings.whatsapp_webhook_url,
                        json={"recipient": recipient, "message": message},
                    )
                    response.raise_for_status()
            elif channel == "push":
                async with httpx.AsyncClient(timeout=20) as client:
                    response = await client.post(
                        settings.push_webhook_url,
                        json={"recipient": recipient, "message": message},
                    )
                    response.raise_for_status()
            return "sent", None
        except Exception as exc:  # noqa: BLE001 - delivery errors must be recorded, not crash the scheduler
            return "failed", str(exc)

    def _send_email(self, recipient: str, message: str) -> None:
        if "@" not in recipient:
            raise ValueError("Email recipient is not a valid email address")
        mail = EmailMessage()
        mail["Subject"] = "Timetable Intelligence notification"
        mail["From"] = settings.smtp_from
        mail["To"] = recipient
        mail.set_content(message)
        context = ssl.create_default_context()
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
            if settings.smtp_use_tls:
                smtp.starttls(context=context)
            if settings.smtp_username:
                smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(mail)


async def dispatch_new_test_notifications(database: Database, records: list[TestRecord]) -> None:
    if not records:
        return
    service = NotificationService(database)
    for rule in database.list_notification_rules():
        if not rule.enabled or rule.event_type != "new_test_added":
            continue
        selected = records
        if rule.source_ids:
            selected = [item for item in selected if item.source_id in rule.source_ids]
        if rule.sheet_names:
            wanted = {item.casefold() for item in rule.sheet_names}
            selected = [item for item in selected if item.sheet_name.casefold() in wanted]
        if rule.classes:
            selected = [item for item in selected if _matches(item.class_name, rule.classes)]
        if rule.subjects:
            selected = [item for item in selected if _matches(item.subject, rule.subjects)]
        if not selected:
            continue
        message = build_test_notification_message(database, rule, new_records=selected)
        suffix = "new-tests:" + ":".join(sorted(item.id for item in selected))
        await service.send_scheduled(rule, message, datetime.now(INDIA_TIMEZONE), suffix)


async def run_due_notifications(database: Database) -> None:
    now = datetime.now(INDIA_TIMEZONE).replace(second=0, microsecond=0)
    service = NotificationService(database)
    for rule in database.list_notification_rules():
        if not rule.enabled:
            continue
        if rule.event_type == "before_class":
            minutes = rule.minutes_before or 0
            for entry in _rule_entries(database, rule, now.date()):
                if entry.start_time is None:
                    continue
                class_at = datetime.combine(now.date(), entry.start_time, tzinfo=INDIA_TIMEZONE)
                due_at = class_at - timedelta(minutes=minutes)
                if due_at != now:
                    continue
                suffix = f"class:{entry.id}:{due_at.isoformat()}"
                message = build_notification_message(database, rule, class_entry=entry)
                await service.send_scheduled(rule, message, due_at, suffix)
            continue

        scheduled_test_events = {"test_app_status", "test_result_dashboard", "test_video_solution"}
        if rule.event_type not in {"daily_timetable", "weekly_timetable", "timetable_not_updated", *scheduled_test_events}:
            continue
        if not rule.send_time:
            continue
        rule_time = time.fromisoformat(rule.send_time)
        if (now.hour, now.minute) != (rule_time.hour, rule_time.minute):
            continue
        if rule.event_type in {"weekly_timetable", *scheduled_test_events} and now.weekday() != (rule.weekday or 0):
            continue
        target = now.date()
        suffix = f"scheduled:{rule.event_type}:{target.isoformat()}:{rule.send_time}"
        message = (
            build_test_notification_message(database, rule)
            if rule.event_type in scheduled_test_events
            else build_notification_message(database, rule, target_date=target)
        )
        await service.send_scheduled(rule, message, now, suffix)
