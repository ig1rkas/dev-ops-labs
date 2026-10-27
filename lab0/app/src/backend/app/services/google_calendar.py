from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from hashlib import sha1
from threading import Lock
from urllib.parse import parse_qs, quote, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener
from zoneinfo import ZoneInfo

import recurring_ical_events
from icalendar import Calendar


MOSCOW_TZ = ZoneInfo("Europe/Moscow")
ALLOWED_GOOGLE_CALENDAR_HOSTS = {"calendar.google.com", "www.google.com", "google.com"}
CALENDAR_CACHE_TTL = timedelta(minutes=5)
MAX_CALENDAR_BYTES = 5 * 1024 * 1024


@dataclass(frozen=True)
class CalendarLoadResult:
    lessons: list[dict]
    error: str | None = None


_calendar_cache: dict[str, tuple[datetime, CalendarLoadResult]] = {}
_calendar_cache_lock = Lock()


def is_lesson_event_title(value: str) -> bool:
    """Match the Russian lesson prefix independently of letter case."""

    return value.strip().casefold().startswith("урок")


def _allowed_google_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme == "https" and (parsed.hostname or "").lower() in ALLOWED_GOOGLE_CALENDAR_HOSTS


def normalize_google_calendar_url(value: str | None) -> str | None:
    """Return a fetchable Google iCal URL while rejecting arbitrary hosts."""

    clean = (value or "").strip()
    if not clean:
        return None
    if clean.startswith("webcal://"):
        clean = f"https://{clean[len('webcal://') :]}"
    if not _allowed_google_url(clean):
        raise ValueError("Нужна ссылка Google Calendar с адресом calendar.google.com")

    parsed = urlparse(clean)
    path = parsed.path.rstrip("/")
    if path.endswith(".ics") and "/calendar/ical/" in path:
        return clean

    # Google also exposes an embed URL. It can be converted to an iCal feed
    # when the calendar itself is public. Private calendars should use the
    # Secret address in iCal format from Google Calendar settings.
    source = parse_qs(parsed.query).get("src", [None])[0]
    if "/calendar/embed" in path and source:
        encoded_source = quote(source, safe="")
        return f"https://calendar.google.com/calendar/ical/{encoded_source}/public/basic.ics"

    raise ValueError("Вставьте публичный или секретный адрес календаря в формате iCal (.ics)")


class _GoogleOnlyRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        if not _allowed_google_url(new_url):
            raise ValueError("Google Calendar перенаправил запрос на недопустимый адрес")
        return super().redirect_request(request, file_pointer, code, message, headers, new_url)


def _as_moscow_datetime(value: date | datetime) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=MOSCOW_TZ)
        return value.astimezone(MOSCOW_TZ)
    return datetime.combine(value, time.min, tzinfo=MOSCOW_TZ)


def _event_duration_minutes(event, starts_at: datetime) -> int:
    end_property = event.get("DTEND")
    if end_property is not None:
        ends_at = _as_moscow_datetime(end_property.dt)
        return max(1, int((ends_at - starts_at).total_seconds() // 60))
    duration_property = event.get("DURATION")
    if duration_property is not None:
        duration = duration_property.dt
        if isinstance(duration, timedelta):
            return max(1, int(duration.total_seconds() // 60))
    return 60


def parse_google_calendar(ical_body: bytes, teacher_name: str, now: datetime | None = None) -> list[dict]:
    current = (now or datetime.now(MOSCOW_TZ)).astimezone(MOSCOW_TZ)
    range_start = current - timedelta(days=35)
    range_end = current + timedelta(days=400)
    calendar = Calendar.from_ical(ical_body)
    events = recurring_ical_events.of(calendar).between(range_start, range_end)
    lessons = []

    for event in events:
        summary = str(event.get("SUMMARY", "")).strip()
        if not is_lesson_event_title(summary):
            continue
        start_property = event.get("DTSTART")
        if start_property is None:
            continue
        starts_at = _as_moscow_datetime(start_property.dt)
        uid = str(event.get("UID", summary))
        occurrence_key = f"{uid}|{starts_at.isoformat()}"
        description = str(event.get("DESCRIPTION", "")).strip()
        location = str(event.get("LOCATION", "")).strip()
        detail = next((part for part in (description, location) if part), "Google Calendar")
        lessons.append(
            {
                "id": f"gcal-{sha1(occurrence_key.encode('utf-8')).hexdigest()[:16]}",
                "date": starts_at.date().isoformat(),
                "day_offset": starts_at.weekday(),
                "time": starts_at.strftime("%H:%M"),
                "duration": f"{_event_duration_minutes(event, starts_at)} мин",
                "course": summary,
                "topic": detail,
                "status": "calendar",
                "student": "",
                "teacher": teacher_name,
                "source": "google_calendar",
            }
        )

    lessons.sort(key=lambda lesson: (lesson["date"], lesson["time"], str(lesson["id"])))
    return lessons


def load_google_calendar_lessons(
    calendar_url: str | None,
    teacher_name: str,
    *,
    force_refresh: bool = False,
) -> CalendarLoadResult:
    if not calendar_url:
        return CalendarLoadResult(lessons=[])

    now = datetime.now(MOSCOW_TZ)
    if not force_refresh:
        with _calendar_cache_lock:
            cached = _calendar_cache.get(calendar_url)
            if cached is not None and now - cached[0] < CALENDAR_CACHE_TTL:
                return cached[1]

    try:
        normalized_url = normalize_google_calendar_url(calendar_url)
        request = Request(normalized_url, headers={"User-Agent": "idioma-calendar-sync/1.0", "Accept": "text/calendar"})
        opener = build_opener(_GoogleOnlyRedirectHandler())
        with opener.open(request, timeout=8) as response:
            body = response.read(MAX_CALENDAR_BYTES + 1)
        if len(body) > MAX_CALENDAR_BYTES:
            raise ValueError("Файл календаря слишком большой")
        result = CalendarLoadResult(lessons=parse_google_calendar(body, teacher_name, now=now))
    except Exception as exc:  # Calendar sync must not break the whole dashboard.
        result = CalendarLoadResult(lessons=[], error=f"Не удалось загрузить Google Calendar: {exc}")

    with _calendar_cache_lock:
        _calendar_cache[calendar_url] = (now, result)
    return result
