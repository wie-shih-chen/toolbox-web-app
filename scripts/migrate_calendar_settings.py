"""
Migration: Add calendar notification settings columns.
Uses plain sqlite3 – no Flask dependencies required.

Run:  python scripts/migrate_calendar_settings.py
"""
import sqlite3, os, sys

# Find the database path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Try to read DATABASE_URL from .env
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

# Fallback: look for common db file names
if not db_path:
    for name in ['app.db', 'database.db', 'toolbox.db', 'site.db']:
        candidate = os.path.join(BASE_DIR, name)
        if os.path.exists(candidate):
            db_path = candidate
            break

if not db_path:
    print("❌ Could not find SQLite database. Please edit the db_path variable manually.")
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
