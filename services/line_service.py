from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import TextSendMessage, ImageSendMessage
from flask import current_app
import os

class LineService:
    _line_bot_api = None
    _handler = None

    @classmethod
    def init_app(cls, app):
        token = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
        secret = os.environ.get('LINE_CHANNEL_SECRET')
        
        if token and secret:
            cls._line_bot_api = LineBotApi(token)
            cls._handler = WebhookHandler(secret)
        else:
            print("LINE Bot credentials not found in env.")

    @classmethod
    def get_handler(cls):
        return cls._handler

    @classmethod
    def push_message(cls, user_id, text):
        if not cls._line_bot_api:
            return False
            
        try:
            # LINE Limit is 5000 chars. We split at 4000 to be safe.
            max_length = 4000
            
            if len(text) <= max_length:
                cls._line_bot_api.push_message(user_id, TextSendMessage(text=text))
            else:
                # Split into chunks
                chunks = [text[i:i+max_length] for i in range(0, len(text), max_length)]
                for chunk in chunks:
                    cls._line_bot_api.push_message(user_id, TextSendMessage(text=chunk))
                    
            return True
        except Exception as e:
            print(f"LINE Push Error: {e}")
            return False

    @classmethod
    def push_image(cls, user_id, image_url, thumbnail_url=None):
        if not cls._line_bot_api:
            return False
        try:
            if thumbnail_url is None:
                thumbnail_url = image_url
            
            message = ImageSendMessage(
                original_content_url=image_url,
                preview_image_url=thumbnail_url
            )
            cls._line_bot_api.push_message(user_id, message)
            return True
        except Exception as e:
            print(f"LINE Push Image Error: {e}")
            return False

    @classmethod
    def push_to_user(cls, app_user_id, text=None, image_url=None, thumbnail_url=None, module=None):
        """
        Sends a LINE message to all bindings of a specific internal user_id,
        respecting the permissions of each binding.
        """
        from models import LineBinding, UserSettings
        import json

        bindings = LineBinding.query.filter_by(user_id=app_user_id).all()
        
        sent_nicknames = []

        if not bindings:
            # Fallback to legacy single binding
            setting = UserSettings.query.filter_by(user_id=app_user_id).first()
            if setting and setting.line_user_id:
                if text:
                    cls.push_message(setting.line_user_id, text)
                if image_url:
                    cls.push_image(setting.line_user_id, image_url, thumbnail_url)
                sent_nicknames.append('預設綁定帳號')
            return sent_nicknames

        for binding in bindings:
            if module:
                try:
                    perms = json.loads(binding.permissions or '[]')
                    if module not in perms:
                        continue
                except Exception:
                    pass
            
            if text:
                cls.push_message(binding.line_user_id, text)
            if image_url:
                cls.push_image(binding.line_user_id, image_url, thumbnail_url)
                
            sent_nicknames.append(binding.nickname or '未命名')
                
        return sent_nicknames
