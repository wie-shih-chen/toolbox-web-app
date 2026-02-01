from flask_mail import Message
from flask import render_template, current_app
import random
import string
from extensions import mail

class EmailService:
    @staticmethod
    def send_email(to, subject, template, **kwargs):
        msg = Message(subject, recipients=[to])
        msg.html = render_template(template, **kwargs)
        try:
            mail.send(msg)
            return True
        except Exception as e:
            print(f"Failed to send email: {e}")
            return False

    @staticmethod
    def send_welcome_email(user):
        return EmailService.send_email(
            user.email,
            '歡迎加入工具箱 Web！',
            'email/welcome.html',
            user=user
        )

    @staticmethod
    def send_password_reset_email(user, code):
        return EmailService.send_email(
            user.email,
            '重設您的密碼',
            'email/reset_password.html',
            user=user,
            code=code
        )
    
    @staticmethod
    def generate_verification_code(length=6):
        """Generate a random numeric code."""
        return ''.join(random.choices(string.digits, k=length))
