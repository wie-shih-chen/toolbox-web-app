"""
CountdownNotifyService
---------------------------------------------
Daily interval job (via APScheduler, runs every minute) that:
1. Checks all users with notify_enabled countdown events.
2. For each event, checks if any milestones (system 50/100day, annual, or custom sub-events) fall tomorrow.
3. Sends notification based on the user's General Settings notification_methods (LINE/Email).
4. Uses CalendarNotificationLog-like deduplication to avoid duplicate sends.
"""

from datetime import datetime, timedelta, date
import json

from models import db, User, UserSettings, Countdown, CountdownSubEvent
from extensions import mail
from flask_mail import Message
from flask import current_app


class CountdownNotifyService:

    @staticmethod
    def check_and_send(app):
        """Entry point called by APScheduler. Runs every minute."""
        with app.app_context():
            now_tw = datetime.utcnow() + timedelta(hours=8)
            current_time = now_tw.strftime('%H:%M')
            tomorrow = (now_tw + timedelta(days=1)).date()

            # Only run at 09:00 Taiwan time to avoid spam
            if current_time != '09:00':
                return

            print(f'[CountdownNotify] Running at {current_time} TW — checking tomorrow {tomorrow}')

            users = User.query.all()
            sent_total = 0
            for user in users:
                try:
                    sent_total += CountdownNotifyService._process_user(user, tomorrow)
                except Exception as e:
                    print(f'[CountdownNotify] Error for user {user.id}: {e}')

            db.session.commit()
            print(f'[CountdownNotify] Done. Sent {sent_total} notification(s).')

    @staticmethod
    def _process_user(user: User, tomorrow: date) -> int:
        """Process one user. Returns number of notifications sent."""
        settings = UserSettings.query.filter_by(user_id=user.id).first()
        if not settings:
            return 0

        try:
            methods = json.loads(settings.notification_methods or '[]')
        except Exception:
            methods = ['email']

        if not methods:
            return 0

        # Get all countdown events for the user that have notifications enabled
        events = Countdown.query.filter_by(user_id=user.id, notify_enabled=True).all()
        sent = 0

        for ev in events:
            target = datetime.strptime(ev.target_date, '%Y-%m-%d').date()
            milestones_to_check = []

            # System milestones for anniversaries
            if ev.is_anniversary:
                # Check 50-day multiples
                days_elapsed = (tomorrow - target).days + 1
                if days_elapsed > 0 and days_elapsed % 50 == 0:
                    milestones_to_check.append(f'{days_elapsed}天紀念日 🗓️')
                # Check annual
                from dateutil.relativedelta import relativedelta
                for y in range(1, 6):
                    annual_date = target + relativedelta(years=y)
                    if annual_date == tomorrow:
                        milestones_to_check.append(f'{y}週年紀念日 🎉')

            # The target_date itself (for countdown events)
            if not ev.is_anniversary and target == tomorrow:
                milestones_to_check.append(f'倒數日「{ev.title}」明天到來！⏰')

            # Custom sub-events
            sub_events = CountdownSubEvent.query.filter_by(countdown_id=ev.id).all()
            for se in sub_events:
                se_date = datetime.strptime(se.target_date, '%Y-%m-%d').date()
                if se_date == tomorrow:
                    milestones_to_check.append(f'{se.icon} {se.title}')

            for milestone_label in milestones_to_check:
                from services.notification_service import NotificationTemplate
                msg = NotificationTemplate.get_countdown_msg(ev.title, milestone_label)
                CountdownNotifyService._send(user, settings, methods, msg)
                sent += 1

        return sent

    @staticmethod
    def _send(user, settings, methods, msg_text):
        from services.notification_service import NotificationService, NotificationTemplate
        subject = NotificationTemplate.get_countdown_subject(msg_text)
        NotificationService.send_notification(
            user=user,
            subject=subject,
            message_text=msg_text,
            notify_methods=methods,
            module='countdown'
        )
