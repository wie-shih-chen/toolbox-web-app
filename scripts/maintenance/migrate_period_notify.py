"""
【使用時機】
  新增生理期通知功能時執行。
  1. 新增 user_settings 欄位：
     - period_notify_enabled (Boolean)
     - period_notify_time (String)
     - period_notify_days_before (Integer)
  2. 建立 period_notification_log 資料表。

【執行方式】
  python scripts/maintenance/migrate_period_notify.py
"""
import sys
import os

os.environ['SKIP_SCHEDULER'] = '1'

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import app, db
from sqlalchemy import text

with app.app_context():
    print("Running migration: Period tracker notifications...")
    
    # 1. Create tables (handles PeriodNotificationLog)
    db.create_all()
    print("✅ Tables ensured (including period_notification_log).")
    
    # 2. Add columns to user_settings
    try:
        with db.engine.connect() as conn:
            # Check and add period_notify_enabled
            try:
                conn.execute(text("SELECT period_notify_enabled FROM user_settings LIMIT 1"))
                print("Column 'period_notify_enabled' already exists.")
            except Exception:
                print("Adding 'period_notify_enabled' column...")
                conn.execute(text("ALTER TABLE user_settings ADD COLUMN period_notify_enabled BOOLEAN DEFAULT 1"))
                conn.commit()
            
            # Check and add period_notify_time
            try:
                conn.execute(text("SELECT period_notify_time FROM user_settings LIMIT 1"))
                print("Column 'period_notify_time' already exists.")
            except Exception:
                print("Adding 'period_notify_time' column...")
                conn.execute(text("ALTER TABLE user_settings ADD COLUMN period_notify_time VARCHAR(5) DEFAULT '08:00'"))
                conn.commit()

            # Check and add period_notify_days_before
            try:
                conn.execute(text("SELECT period_notify_days_before FROM user_settings LIMIT 1"))
                print("Column 'period_notify_days_before' already exists.")
            except Exception:
                print("Adding 'period_notify_days_before' column...")
                conn.execute(text("ALTER TABLE user_settings ADD COLUMN period_notify_days_before INTEGER DEFAULT 3"))
                conn.commit()
                
            print("✅ Migration successful!")
    except Exception as e:
        print(f"❌ Migration failed: {e}")
