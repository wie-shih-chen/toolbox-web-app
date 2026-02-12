
import sys
import os

# Create a dummy app context to run the migration
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db
from sqlalchemy import text

with app.app_context():
    print("Running migration: Add monthly_report_day to user_settings table...")
    try:
        # Check if column exists
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
