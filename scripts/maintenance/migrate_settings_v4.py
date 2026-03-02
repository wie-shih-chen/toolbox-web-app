"""
【狀態】已執行過，通常不需要再跑。

【使用時機】
  若 user_settings 資料表缺少 monthly_report_day 欄位時執行。
  新增欄位：
    - monthly_report_day  每月報表寄送日（預設第5日）

【執行方式】
  cd ~/toolbox-web-app
  python scripts/maintenance/migrate_settings_v4.py

【依賴】
  需要 Flask 虛擬環境（因使用 SQLAlchemy text）。
  先啟用 venv：source venv/bin/activate
"""
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import app, db
from sqlalchemy import text

with app.app_context():
    print("Running migration: Add monthly_report_day to user_settings table...")
    try:
        with db.engine.connect() as conn:
            try:
                conn.execute(text("SELECT monthly_report_day FROM user_settings LIMIT 1"))
                print("Column 'monthly_report_day' already exists. Skipping.")
            except Exception:
                print("Adding 'monthly_report_day' column...")
                conn.execute(text("ALTER TABLE user_settings ADD COLUMN monthly_report_day INTEGER DEFAULT 5"))
                conn.commit()
                print("Migration successful!")
    except Exception as e:
        print(f"Migration failed: {e}")
