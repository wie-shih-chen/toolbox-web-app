from flask import current_app
from extensions import mail
from flask_mail import Message
import json
import logging

logger = logging.getLogger(__name__)

class NotificationTemplate:
    """
    統一管理所有推播通知的文字內容，方便一次性檢修與修改。
    """
    
    # --- 1. 行事曆 (Calendar) ---
    @staticmethod
    def get_calendar_msg(event_title, cal_name):
        return f"📅 行事曆提醒：明天 {event_title}\n（日曆：{cal_name}）"
        
    @staticmethod
    def get_calendar_subject(event_title):
        return f"📅 行事曆提醒：明天 {event_title}"

    # --- 2. 倒數日 (Countdown) ---
    @staticmethod
    def get_countdown_msg(title, milestone_label):
        return f"💕 「{title}」提醒：明天是 {milestone_label}"
        
    @staticmethod
    def get_countdown_subject(msg_text):
        return f"💕 倒數日提醒：{msg_text[:50]}"

    # --- 3. 日常提醒 (Reminder) ---
    @staticmethod
    def get_reminder_msg(title, description, remind_time):
        return f"🔔 [提醒] {title}\n\n{description or ''}\n\n時間: {remind_time}"
        
    @staticmethod
    def get_reminder_subject(title):
        return f"🔔 提醒: {title}"

    # --- 4. 生理期 (Period) ---
    @staticmethod
    def get_period_msg(days_before, date_str):
        return f"🩸 生理期提醒：預計在 {days_before} 天後 ({date_str}) 開始，請預作準備！"
        
    @staticmethod
    def get_period_subject():
        return "🩸 生理期提醒"

    # --- 5. 排卵期 (Ovulation) ---
    @staticmethod
    def get_ovulation_msg(days_before, date_str):
        return f"🌸 排卵期提醒：預計在 {days_before} 天後 ({date_str}) 到來，這段期間受孕機率較高哦！"
        
    @staticmethod
    def get_ovulation_subject():
        return "🌸 排卵期提醒"

class NotificationService:
    @staticmethod
    def send_notification(user, subject, message_text, notify_methods=None, module=None):
        """
        Sends a notification to the user via their preferred methods.
        If notify_methods is None, checks user.settings.notification_methods or defaults to ['email'].
        Returns True if at least one method succeeded.
        """
        if notify_methods is None:
            if hasattr(user, 'settings') and user.settings and hasattr(user.settings, 'notification_methods') and user.settings.notification_methods:
                try:
                    notify_methods = json.loads(user.settings.notification_methods)
                except:
                    notify_methods = ['email']
            else:
                notify_methods = ['email']
                
        if not notify_methods:
            return False
            
        success = False
        prefix = f"[{module or 'System'}] "
        
        # 1. LINE Notify
        if 'line' in notify_methods:
            try:
                from services.line_service import LineService
                if LineService.push_to_user(user.id, message_text, module=module):
                    print(f"{prefix}LINE sent to user {user.id}")
                    success = True
            except Exception as e:
                print(f"{prefix}LINE send failed for user {user.id}: {e}")

        # 2. Email Notify
        if 'email' in notify_methods and user.email:
            try:
                sender = current_app.config.get('MAIL_USERNAME')
                msg = Message(
                    subject=subject,
                    recipients=[user.email],
                    body=message_text,
                    sender=sender
                )
                mail.send(msg)
                print(f"{prefix}Email sent to {user.email}")
                success = True
            except Exception as e:
                print(f"{prefix}Email send failed for user {user.id}: {e}")
                
        return success
