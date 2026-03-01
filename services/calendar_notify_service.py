"""
CalendarNotifyService
------------------------------------
Daily scheduler job that:
1. Scans every UserCalendar for all users.
2. Finds ICS events whose start date == tomorrow (Taiwan time).
3. Sends a notification via the user's preferred method (LINE / Email).
4. Logs each sent notification to CalendarNotificationLog to prevent duplicates.
"""

from datetime import datetime, timedelta, date
import json
import os

import requests as http_req

from models import db, User, UserCalendar, UserSettings, CalendarNotificationLog
from extensions import mail
from flask_mail import Message
from flask import current_app


# ---------------------------------------------------------------------------
# ICS helper
# ---------------------------------------------------------------------------

def _get_tomorrow_events(cal_record: UserCalendar, tomorrow: date) -> list:
    """
    Fetch and parse the ICS source of `cal_record`, returning a list of dicts
    for events whose start date is exactly `tomorrow`.

    Returns: [{'title': str, 'start': date, 'key': str}]
    """
    try:
        from icalendar import Calendar
    except ImportError:
        print("[CalNotify] icalendar not installed – skipping ICS parse.")
        return []

    try:
        if cal_record.source_type == 'url':
            resp = http_req.get(cal_record.source, timeout=15)
            content = resp.content
        else:
            if not os.path.exists(cal_record.source):
                return []
            with open(cal_record.source, 'rb') as f:
                content = f.read()
    except Exception as e:
        print(f"[CalNotify] Failed to fetch cal {cal_record.id}: {e}")
        return []

    events = []
    try:
        cal = Calendar.from_ical(content)
        for component in cal.walk():
            if component.name != 'VEVENT':
                continue
            dtstart = component.get('DTSTART')
            if not dtstart:
                continue
            start = dtstart.dt
            # icalendar returns date or datetime
            start_date = start if isinstance(start, date) and not isinstance(start, datetime) else start.date()

            if start_date != tomorrow:
                continue

            title = str(component.get('SUMMARY', '（無標題）'))
            # Build a deterministic key for de-dup
            key = f"{cal_record.id}:{start_date.isoformat()}:{title[:100]}"
            events.append({'title': title, 'start': start_date, 'key': key})
    except Exception as e:
        print(f"[CalNotify] ICS parse error for cal {cal_record.id}: {e}")

    return events


# ---------------------------------------------------------------------------
# Main service
# ---------------------------------------------------------------------------

class CalendarNotifyService:

    @staticmethod
    def check_and_send(app):
        """Entry point called by the APScheduler cron job."""
        with app.app_context():
            # Taiwan Time = UTC+8
            now_tw = datetime.utcnow() + timedelta(hours=8)
            tomorrow = (now_tw + timedelta(days=1)).date()
            today_str = now_tw.strftime('%Y-%m-%d')

            print(f"[CalNotify] Running for tomorrow={tomorrow} (today={today_str})")

            # Collect all users who have at least one calendar
            cal_user_ids = db.session.query(UserCalendar.user_id).distinct().all()
            user_ids = [row[0] for row in cal_user_ids]

            sent_total = 0

            for user_id in user_ids:
                try:
                    sent_total += CalendarNotifyService._process_user(
                        user_id, tomorrow, today_str
                    )
                except Exception as e:
                    print(f"[CalNotify] Error processing user {user_id}: {e}")

            if sent_total:
                db.session.commit()
            print(f"[CalNotify] Done. Sent {sent_total} notification(s).")

    # ------------------------------------------------------------------

    @staticmethod
    def _process_user(user_id: int, tomorrow: date, today_str: str) -> int:
        """Process one user. Returns number of notifications sent."""
        settings = UserSettings.query.filter_by(user_id=user_id).first()
        if not settings:
            return 0

        try:
            methods = json.loads(settings.notification_methods)
        except Exception:
            methods = ['email']

        if not methods:
            return 0

        user = User.query.get(user_id)
        if not user:
            return 0

        calendars = UserCalendar.query.filter_by(user_id=user_id).all()
        sent = 0

        for cal in calendars:
            events = _get_tomorrow_events(cal, tomorrow)
            for ev in events:
                # De-dup check
                already_sent = CalendarNotificationLog.query.filter_by(
                    user_id=user_id,
                    cal_id=cal.id,
                    event_key=ev['key'],
                ).first()

                if already_sent:
                    continue

                # Send
                msg_text = f"📅 行事曆提醒：明天 {ev['title']}"
                CalendarNotifyService._send(user, settings, methods, ev['title'], cal.name)

                # Log it
                log = CalendarNotificationLog(
                    user_id=user_id,
                    cal_id=cal.id,
                    event_key=ev['key'],
                    sent_date=today_str,
                )
                db.session.add(log)
                sent += 1

        return sent

    # ------------------------------------------------------------------

    @staticmethod
    def _send(user, settings, methods: list, event_title: str, cal_name: str):
        """Dispatch notification via LINE and/or Email."""
        msg_text = f"📅 行事曆提醒：明天 {event_title}\n（日曆：{cal_name}）"

        if 'line' in methods and settings.line_user_id:
            try:
                from services.line_service import LineService
                LineService.push_message(settings.line_user_id, msg_text)
                print(f"[CalNotify] LINE sent to user {user.id}: {event_title}")
            except Exception as e:
                print(f"[CalNotify] LINE send failed for user {user.id}: {e}")

        if 'email' in methods and user.email:
            try:
                sender = current_app.config.get('MAIL_USERNAME')
                if not sender:
                    print("[CalNotify] MAIL_USERNAME not set, skipping email.")
                else:
                    msg = Message(
                        subject=f"📅 行事曆提醒：明天 {event_title}",
                        recipients=[user.email],
                        body=msg_text,
                        sender=sender,
                    )
                    mail.send(msg)
                    print(f"[CalNotify] Email sent to {user.email}: {event_title}")
            except Exception as e:
                print(f"[CalNotify] Email send failed for user {user.id}: {e}")
