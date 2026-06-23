"""
Migration: 新增旅程規劃器資料表
執行方式：python scripts/migrate_travel.py
"""
import sqlite3
import os

DB_CANDIDATES = ['app.db', 'instance/app.db', 'site.db', 'instance/site.db']
db_path = None
for p in DB_CANDIDATES:
    if os.path.exists(p):
        db_path = p
        break

if not db_path:
    print('❌ 找不到資料庫檔案，請確認路徑')
    exit(1)

print(f'✅ 找到資料庫：{db_path}')

conn = sqlite3.connect(db_path)
cur  = conn.cursor()

# 取得現有資料表清單
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
existing_tables = {r[0] for r in cur.fetchall()}

# --- 建立 trip_plan 資料表 ---
if 'trip_plan' in existing_tables:
    print('  ⏭  trip_plan 已存在，跳過')
else:
    cur.execute('''
        CREATE TABLE trip_plan (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES user(id),
            title       VARCHAR(100) NOT NULL,
            description VARCHAR(500),
            start_date  VARCHAR(10),
            end_date    VARCHAR(10),
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    print('  ✅ 建立資料表：trip_plan')

# --- 建立 trip_stop 資料表 ---
if 'trip_stop' in existing_tables:
    print('  ⏭  trip_stop 已存在，跳過')
else:
    cur.execute('''
        CREATE TABLE trip_stop (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            trip_id           INTEGER NOT NULL REFERENCES trip_plan(id),
            day_index         INTEGER DEFAULT 0,
            order_index       INTEGER DEFAULT 0,
            name              VARCHAR(200) NOT NULL,
            address           VARCHAR(500),
            lat               REAL,
            lng               REAL,
            note              VARCHAR(500),
            estimated_expense REAL DEFAULT 0.0,
            is_completed      BOOLEAN DEFAULT 0,
            created_at        DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    print('  ✅ 建立資料表：trip_stop')

conn.commit()
conn.close()
print('\n🎉 Migration 完成！旅程規劃器資料表已就緒。')
