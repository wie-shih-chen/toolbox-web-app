"""
Migration: Add calendar notification settings columns.
Run once on the server:  python scripts/migrate_calendar_settings.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

from app import app
from models import db
from sqlalchemy import text

MIGRATIONS = [
    # UserSettings – calendar notification columns
    "ALTER TABLE user_settings ADD COLUMN calendar_notify_enabled BOOLEAN DEFAULT 1",
    "ALTER TABLE user_settings ADD COLUMN calendar_notify_time VARCHAR(5) DEFAULT '20:00'",
    # UserCalendar – per-calendar mute toggle
    "ALTER TABLE user_calendar ADD COLUMN notify_enabled BOOLEAN DEFAULT 1",
]

with app.app_context():
    with db.engine.connect() as conn:
        for stmt in MIGRATIONS:
            try:
                conn.execute(text(stmt))
                print(f"✅ {stmt[:60]}...")
            except Exception as e:
                # Column likely already exists
                print(f"⚠️  Skipped (might exist): {e}")
        conn.commit()
    print("\n✅ Migration complete.")
