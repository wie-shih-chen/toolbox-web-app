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
            cls._line_bot_api.push_message(user_id, TextSendMessage(text=text))
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
