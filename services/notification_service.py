from flask import current_app
from extensions import mail
from flask_mail import Message
import json
import logging

logger = logging.getLogger(__name__)

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
