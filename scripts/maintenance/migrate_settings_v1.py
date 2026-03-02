"""
【狀態】已執行過，通常不需要再跑。

【使用時機】
  若從舊版（無下列欄位）升級到含有這些欄位的版本時執行。
  新增欄位：user_settings 資料表
    - editable_month_range  可編輯月份範圍
    - default_start_time    預設上班時間
    - default_end_time      預設下班時間
    - target_income         月收入目標
    - budget_alert_threshold 預算警戒水位

【執行方式】
  cd ~/toolbox-web-app
  python scripts/maintenance/migrate_settings_v1.py

【依賴】
  純 sqlite3，不需要 Flask 虛擬環境套件。
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'app.db')

if not os.path.exists(DB_PATH):
    print(f"Database not found at {DB_PATH}, skipping migration.")
    exit(0)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

def column_exists(table, col):
    cursor.execute(f"PRAGMA table_info({table})")
    cols = [info[1] for info in cursor.fetchall()]
    return col in cols

TABLE = 'user_settings'

if not column_exists(TABLE, 'editable_month_range'):
    print("Adding editable_month_range...")
    cursor.execute(f"ALTER TABLE {TABLE} ADD COLUMN editable_month_range INTEGER DEFAULT 1")

if not column_exists(TABLE, 'default_start_time'):
    print("Adding default_start_time...")
    cursor.execute(f"ALTER TABLE {TABLE} ADD COLUMN default_start_time VARCHAR(5) DEFAULT '09:00'")

if not column_exists(TABLE, 'default_end_time'):
    print("Adding default_end_time...")
    cursor.execute(f"ALTER TABLE {TABLE} ADD COLUMN default_end_time VARCHAR(5) DEFAULT '18:00'")

if not column_exists(TABLE, 'target_income'):
    print("Adding target_income...")
    cursor.execute(f"ALTER TABLE {TABLE} ADD COLUMN target_income INTEGER DEFAULT 0")

if not column_exists(TABLE, 'budget_alert_threshold'):
    print("Adding budget_alert_threshold...")
    cursor.execute(f"ALTER TABLE {TABLE} ADD COLUMN budget_alert_threshold INTEGER DEFAULT 80")

conn.commit()
conn.close()
print("Migration V1 completed.")
