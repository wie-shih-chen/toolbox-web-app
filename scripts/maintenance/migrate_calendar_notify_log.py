"""
【狀態】已執行過，通常不需要再跑。

【使用時機】
  部署「行事曆通知」功能後，若 calendar_notification_log 資料表不存在時執行。
  此腳本透過 db.create_all() 建立所有尚未存在的資料表（包含 CalendarNotificationLog）。

【執行方式】
  cd ~/toolbox-web-app
  source venv/bin/activate
  python scripts/maintenance/migrate_calendar_notify_log.py

【依賴】
  需要 Flask 虛擬環境（會 import app 與 models）。
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), '.env'))

from app import app
from models import db

with app.app_context():
    db.create_all()
    print("✅ calendar_notification_log table ensured.")
