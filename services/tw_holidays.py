"""
tw_holidays.py — Taiwan National Holiday Helper
-------------------------------------------------
Fetches Taiwan public holidays from Google Calendar ICS and
returns them as {YYYY-MM-DD: holiday_name} for a given year.

ICS Source:
  https://calendar.google.com/calendar/ical/zh-tw.taiwan%23holiday%40group.v.calendar.google.com/public/basic.ics

Usage:
  from services.tw_holidays import get_holidays, is_holiday

  h = get_holidays(2025)          # {date_str: name}
  name = is_holiday('2025-05-01') # '勞動節' or None
"""

import requests as http_req
from datetime import datetime, date

# Module-level cache; keyed by year
_cache: dict[int, dict] = {}

TW_HOLIDAY_ICS_URL = (
    "https://calendar.google.com/calendar/ical/"
    "zh-tw.taiwan%23holiday%40group.v.calendar.google.com/public/basic.ics"
)


def _fetch_and_parse_all() -> dict:
    """
    Fetch the ICS once and return a dict of ALL dates.
    {YYYY-MM-DD: holiday_name}
    """
    try:
        from icalendar import Calendar
    except ImportError:
        print("[tw_holidays] icalendar not installed, holiday detection disabled.")
        return {}

    try:
        resp = http_req.get(TW_HOLIDAY_ICS_URL, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"[tw_holidays] Failed to fetch ICS: {e}")
        return {}

    result = {}
    try:
        cal = Calendar.from_ical(resp.content)
        for component in cal.walk():
            if component.name != 'VEVENT':
                continue
            dtstart = component.get('DTSTART')
            if not dtstart:
                continue
            start = dtstart.dt
            start_date = start if isinstance(start, date) and not isinstance(start, datetime) else start.date()
            name = str(component.get('SUMMARY', '國定假日'))
            # Strip trailing " (substitute)" or " (补假)" style suffixes that Google appends
            name = name.split(' (')[0].strip()
            result[start_date.isoformat()] = name
    except Exception as e:
        print(f"[tw_holidays] ICS parse error: {e}")

    return result


# Full calendar cache (all years in one ICS)
_all_holidays: dict | None = None


def _get_all() -> dict:
    global _all_holidays
    if _all_holidays is None:
        _all_holidays = _fetch_and_parse_all()
    return _all_holidays


def get_holidays(year: int) -> dict:
    """
    Return {YYYY-MM-DD: holiday_name} for the specified year.
    Results are cached in memory per year.
    """
    if year in _cache:
        return _cache[year]

    all_h = _get_all()
    year_h = {k: v for k, v in all_h.items() if k.startswith(str(year))}
    _cache[year] = year_h
    return year_h


def is_holiday(date_str: str) -> str | None:
    """
    Check if date_str (YYYY-MM-DD) is a Taiwan national holiday.
    Returns the holiday name if it is, or None if not.
    """
    try:
        year = int(date_str[:4])
    except (ValueError, TypeError):
        return None
    return get_holidays(year).get(date_str)
