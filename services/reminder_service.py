from models import db, Reminder, UserSettings
from extensions import mail
from flask_mail import Message
from services.line_service import LineService
from datetime import datetime, timedelta
import json
import calendar

class ReminderService:
    @staticmethod
    def get_user_reminders(user_id):
        return Reminder.query.filter_by(user_id=user_id).order_by(Reminder.created_at.desc()).all()

    @staticmethod
    def create_reminder(user_id, data):
        # Data validation
        title = data.get('title')
        remind_time = data.get('remind_time')
        
        if not title or not remind_time:
            return None, "Title and time are required"

        # Use Global Settings for notification methods if not provided
        # (User requested to rely on global settings)
        methods = data.get('notify_method')
        if not methods:
            user_settings = UserSettings.query.filter_by(user_id=user_id).first()
            if user_settings and user_settings.notification_methods:
                try:
                    methods = json.loads(user_settings.notification_methods)
                except:
                    methods = ['line'] # Fallback
            else:
                methods = ['line'] # Default fallback

        reminder = Reminder(
            user_id=user_id,
            title=title,
            description=data.get('description', ''),
            frequency=data.get('frequency', 'once'),
            remind_time=remind_time,
            remind_date=data.get('remind_date'), # Only for 'once'
            weekdays=json.dumps(data.get('weekdays')) if data.get('weekdays') else None,
            notify_method=json.dumps(methods),
            is_active=True
        )
        
        db.session.add(reminder)
        db.session.commit()
        return reminder, None

    @staticmethod
    def update_reminder(reminder_id, user_id, data):
        reminder = Reminder.query.filter_by(id=reminder_id, user_id=user_id).first()
        if not reminder:
            return None, "Reminder not found"
            
        reminder.title = data.get('title', reminder.title)
        reminder.description = data.get('description', reminder.description)
        reminder.frequency = data.get('frequency', reminder.frequency)
        reminder.remind_time = data.get('remind_time', reminder.remind_time)
        reminder.remind_date = data.get('remind_date', reminder.remind_date)
        
        if 'weekdays' in data:
            weekdays = data.get('weekdays')
            reminder.weekdays = json.dumps(weekdays) if weekdays else None

        if 'notify_method' in data:
            reminder.notify_method = json.dumps(data.get('notify_method'))
            
        db.session.commit()
        return reminder, None

    @staticmethod
    def delete_reminder(reminder_id, user_id):
        reminder = Reminder.query.filter_by(id=reminder_id, user_id=user_id).first()
        if reminder:
            db.session.delete(reminder)
            db.session.commit()
            return True
        return False

    @staticmethod
    def toggle_active(reminder_id, user_id):
        reminder = Reminder.query.filter_by(id=reminder_id, user_id=user_id).first()
        if reminder:
            reminder.is_active = not reminder.is_active
            db.session.commit()
            return reminder.is_active
        return None

    # --- Scheduler Logic ---
    
    @staticmethod
    def check_and_send_reminders(app):
        """
        Called by Scheduler every minute.
        Checks all active reminders and sends notifications if due.
        """

        with app.app_context():
            # Force Taiwan Time (UTC+8) to match user input
            now = datetime.utcnow() + timedelta(hours=8)
            current_time = now.strftime("%H:%M")
            print(f"[Scheduler] Checking reminders for time: {current_time} (Date: {now.strftime('%Y-%m-%d')})")

            current_date = now.strftime("%Y-%m-%d")
            weekday_map = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
            current_weekday = now.weekday() # 0=Mon, 6=Sun

            # Optimisation: Filter by time first to reduce set
            # Note: This simple query matches string time "HH:MM". 
            # Ideally reminders should be consistent (e.g. "08:05", not "8:5")
            potential_reminders = Reminder.query.filter_by(is_active=True, remind_time=current_time).all()
            
            sent_count = 0
            
            for r in potential_reminders:
                should_send = False
                
                # Frequency Logic
                if r.frequency == 'once':
                    if r.remind_date == current_date:
                        should_send = True
                
                elif r.frequency == 'daily':
                    should_send = True
                    
                elif r.frequency == 'weekly':
                    # Check if 'weekdays' is set (JSON list of ints)
                    if r.weekdays:
                        try:
                            # Handle both list and string representation of list
                            if isinstance(r.weekdays, str):
                                target_days = json.loads(r.weekdays)
                            else:
                                target_days = r.weekdays # Should be list if handled by SQLAlchemy JSON (but it's String)
                                
                            if current_weekday in target_days:
                                should_send = True
                        except Exception as e:
                            print(f"[Scheduler] Error parsing weekdays for reminder {r.id}: {e}")
                    else:
                        # Fallback for old reminders
                        ref_date_str = r.remind_date
                        if ref_date_str:
                            try:
                                ref_date = datetime.strptime(ref_date_str, "%Y-%m-%d")
                                if ref_date.weekday() == current_weekday:
                                    should_send = True
                            except:
                                pass
                
                # Check duplication (last_sent_at)
                if should_send:
                     if r.last_sent_at:
                         time_diff = now - r.last_sent_at
                         # Prevent double sending within 60 seconds
                         if time_diff.total_seconds() < 60:
                             should_send = False
                
                if should_send:
                    print(f"[Scheduler] Sending reminder: {r.title} to User {r.user_id}")
                    ReminderService.send_notification(r)
                    r.last_sent_at = now
                    
                    if r.frequency == 'once':
                        r.is_active = False
                    
                    sent_count += 1
            
            if sent_count > 0:
                db.session.commit()
                print(f"[Scheduler] Sent {sent_count} reminders.")

    @staticmethod
    def send_notification(reminder):
        methods = json.loads(reminder.notify_method)
        user_settings = UserSettings.query.filter_by(user_id=reminder.user_id).first()
        
        msg_text = f"🔔 [提醒] {reminder.title}\n\n{reminder.description or ''}\n\n時間: {reminder.remind_time}"
        
        # 1. LINE Notify
        if 'line' in methods and user_settings and user_settings.line_user_id:
            LineService.push_message(user_settings.line_user_id, msg_text)
            
        # 2. Email Notify
        if 'email' in methods:
            try:
                # user property now exists via backref in models.py
                user = reminder.user 
                if user and user.email:
                    # Ensure Sender is set
                    sender = current_app.config.get('MAIL_USERNAME') or 'noreply@toolbox.com'
                    
                    msg = Message(
                        subject=f"🔔 提醒: {reminder.title}",
                        recipients=[user.email],
                        body=msg_text,
                        sender=sender
                    )
                    mail.send(msg)
                    print(f"[Scheduler] Email sent to {user.email}")
                else:
                    print(f"[Scheduler] Cannot send email: User {reminder.user_id} has no email address.")
            except Exception as e:
                print(f"[Scheduler] Failed to send email reminder: {e}")
