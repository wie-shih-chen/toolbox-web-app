"""
【狀態】已執行過，通常不需要再跑。

【使用時機】
  部署「行事曆通知設定」功能後，若 user_settings 或 user_calendar 資料表
  缺少下列欄位時執行：
    - user_settings.calendar_notify_enabled  通知開關（預設開啟）
    - user_settings.calendar_notify_time     通知時間（預設 '20:00'）
    - user_calendar.notify_enabled           個別日曆靜音開關（預設開啟）

【執行方式】
  cd ~/toolbox-web-app
  python scripts/maintenance/migrate_calendar_settings.py

【依賴】
  純 sqlite3，不需要 Flask 虛擬環境。自動從 .env 讀取 DB 路徑。
"""
import sqlite3, os, sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

db_path = None
env_file = os.path.join(BASE_DIR, '.env')
if os.path.exists(env_file):
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line.startswith('DATABASE_URL') or line.startswith('SQLALCHEMY_DATABASE_URI'):
                value = line.split('=', 1)[1].strip().strip('"').strip("'")
                if value.startswith('sqlite:///'):
                    path = value[len('sqlite:///'):]
                    db_path = path if os.path.isabs(path) else os.path.join(BASE_DIR, path)
                    break

if not db_path:
    for name in ['app.db', 'database.db', 'toolbox.db', 'site.db']:
        candidate = os.path.join(BASE_DIR, name)
        if os.path.exists(candidate):
            db_path = candidate
            break

if not db_path:
    print("❌ Could not find SQLite database.")
    sys.exit(1)

print(f"📂 Using database: {db_path}")
conn = sqlite3.connect(db_path)
cur = conn.cursor()

MIGRATIONS = [
    ("user_settings",  "calendar_notify_enabled", "INTEGER DEFAULT 1"),
    ("user_settings",  "calendar_notify_time",    "VARCHAR(5) DEFAULT '20:00'"),
    ("user_calendar",  "notify_enabled",           "INTEGER DEFAULT 1"),
]

for table, col, col_def in MIGRATIONS:
    try:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_def}")
        print(f"✅  {table}.{col} added")
    except sqlite3.OperationalError as e:
        print(f"⚠️   Skipped ({e})")

conn.commit()
conn.close()
print("\n✅ Migration complete.")
