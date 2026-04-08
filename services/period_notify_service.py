"""
PeriodNotifyService
-------------------
Interval check (every minute) that:
1. For each user, reads their period_notify_enabled, period_notify_time, and period_notify_days_before settings.
2. Skips users with notifications disabled.
3. Calculates the target notice date (predicted_start - days_before).
4. If today matches target notice date AND now matches notify_time, sends notification.
5. Logs to PeriodNotificationLog to prevent duplicate sends for the same cycle.
"""

from datetime import datetime, timedelta, date
import json
from models import db, User, UserSettings, PeriodNotificationLog
from services.period_service import PeriodService
from extensions import mail
from flask_mail import Message
from flask import current_app

class PeriodNotifyService:

    @staticmethod
    def check_and_send(app):
        """
        Entry point called by the APScheduler interval job (every minute).
        """
        with app.app_context():
            # Taiwan Time (UTC+8)
            now_tw = datetime.utcnow() + timedelta(hours=8)
            current_time = now_tw.strftime('%H:%M')
            today = now_tw.date()
            today_str = now_tw.strftime('%Y-%m-%d')

            # Find users whose notify_time matches current_time
            matching_settings = UserSettings.query.filter_by(
                period_notify_enabled=True,
                period_notify_time=current_time
            ).all()

            if not matching_settings:
                return

            print(f"[PeriodNotify] Triggered at {current_time} for {len(matching_settings)} user(s)")

            sent_total = 0
            for s in matching_settings:
                try:
                    sent_total += PeriodNotifyService._process_user(s.user, s, today, today_str)
                except Exception as e:
                    print(f"[PeriodNotify] Error processing user {s.user_id}: {e}")

            if sent_total:
                db.session.commit()
            print(f"[PeriodNotify] Done. Sent {sent_total} notification(s).")

    @staticmethod
    def _process_user(user, settings, today, today_str) -> int:
        """Process one user. Returns number of notifications sent (0 or 1)."""
        # Get predictions
        period_service = PeriodService(user.id)
        predictions = period_service.get_predictions(months=1)
        
        if not predictions:
            return 0
            
        next_pred = predictions[0]
        pred_start_str = next_pred['period_start']
        pred_start_date = datetime.strptime(pred_start_str, '%Y-%m-%d').date()
        
        # Calculate when to notify
        days_before = settings.period_notify_days_before or 3
        notify_date = pred_start_date - timedelta(days=days_before)
        
        # Is it time to notify?
        if today != notify_date:
            return 0
            
        # Check if already sent for this predicted date
        already_sent = PeriodNotificationLog.query.filter_by(
            user_id=user.id,
            predicted_start_date=pred_start_str
        ).first()
        
        if already_sent:
            return 0

        # Send notification
        try:
            methods = json.loads(settings.notification_methods)
        except:
            methods = ['email']
            
        if not methods:
            return 0
            
        msg_text = f"🩸 生理期提醒：預計在 {days_before} 天後 ({pred_start_str}) 開始，請預作準備！"
        
        success = False
        if 'line' in methods and settings.line_user_id:
            try:
                from services.line_service import LineService
                if LineService.push_message(settings.line_user_id, msg_text):
                    print(f"[PeriodNotify] LINE sent to user {user.id}")
                    success = True
            except Exception as e:
                print(f"[PeriodNotify] LINE send failed for user {user.id}: {e}")

        if 'email' in methods and user.email:
            try:
                sender = current_app.config.get('MAIL_USERNAME')
                msg = Message(
                    subject="🩸 生理期提醒",
                    recipients=[user.email],
                    body=msg_text,
                    sender=sender,
                )
                mail.send(msg)
                print(f"[PeriodNotify] Email sent to {user.email}")
                success = True
            except Exception as e:
                print(f"[PeriodNotify] Email send failed for user {user.id}: {e}")

        if success:
            log = PeriodNotificationLog(
                user_id=user.id,
                predicted_start_date=pred_start_str,
                sent_date=today_str
            )
            db.session.add(log)
            return 1
            
        return 0
