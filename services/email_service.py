from flask_mail import Message
from flask import render_template, current_app
import random
import string
from extensions import mail

class EmailService:
    @staticmethod
    def send_email(to, subject, template, raise_error=False, **kwargs):
        sender = current_app.config.get('MAIL_USERNAME')
        if not sender:
            error_msg = "未設定寄件者 (MAIL_USERNAME)。請檢查 .env 檔案設定。"
            print(error_msg)
            if raise_error:
                raise ValueError(error_msg)
            return False

        msg = Message(subject, recipients=[to], sender=sender)
        msg.html = render_template(template, **kwargs)
        try:
            mail.send(msg)
            return True
        except Exception as e:
            print(f"Failed to send email: {e}")
            if raise_error:
                raise e
            return False

    @staticmethod
    def send_email_with_attachment(to, subject, template, attachment_name, attachment_data, attachment_type, **kwargs):
        msg = Message(subject, recipients=[to])
        msg.html = render_template(template, **kwargs)
        
        try:
            msg.attach(attachment_name, attachment_type, attachment_data)
            mail.send(msg)
            return True
        except Exception as e:
            print(f"Failed to send email with attachment: {e}")
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
    def send_password_reset_email(user, token):
        return EmailService.send_email(
            user.email,
            '重設您的密碼',
            'email/reset_password.html',
            user=user,
            token=token
        )
    
    @staticmethod
    def generate_verification_code(length=6):
        """Generate a random numeric code."""
        return ''.join(random.choices(string.digits, k=length))
