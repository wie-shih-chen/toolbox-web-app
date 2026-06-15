"""
Migration: 新增內建日曆顯示設定欄位
執行方式：python migrate_builtin_cal.py
"""
import sqlite3
import os

# 找到資料庫檔案
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

# 取得現有欄位
existing = {r[1] for r in cur.execute('PRAGMA table_info(user_settings)')}
print(f'現有欄位數：{len(existing)}')

NEW_COLS = [
    ('calendar_notify_enabled', 'BOOLEAN',    '1'),
    ('calendar_notify_time',    'VARCHAR(5)',  "'20:00'"),
    ('builtin_salary_name',     'VARCHAR(50)', "'🏷 班表'"),
    ('builtin_salary_color',    'VARCHAR(10)', "'#6366f1'"),
    ('builtin_period_name',     'VARCHAR(50)', "'🩸 週期追蹤'"),
    ('builtin_period_color',    'VARCHAR(10)', "'#ff4d4f'"),
]

for col, dtype, default in NEW_COLS:
    if col in existing:
        print(f'  ⏭  {col} 已存在，跳過')
    else:
        cur.execute(f'ALTER TABLE user_settings ADD COLUMN {col} {dtype} DEFAULT {default}')
        print(f'  ✅ 新增欄位：{col}')

conn.commit()
conn.close()
print('\n🎉 Migration 完成！')
