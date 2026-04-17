import os
import sys

# Add the project directory to the path so we can import the `app`
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import app
from models import db
from sqlalchemy import text

def add_columns_to_tables():
    with app.app_context():
        try:
            # Add columns to user_settings
            try:
                db.session.execute(text("ALTER TABLE user_settings ADD COLUMN period_notify_period BOOLEAN DEFAULT 1"))
                print("✅ added 'period_notify_period' to user_settings")
            except Exception as e:
                print("⚠ 'period_notify_period' could not be added or already exists:", e)
                
            try:
                db.session.execute(text("ALTER TABLE user_settings ADD COLUMN period_notify_ovulation BOOLEAN DEFAULT 0"))
                print("✅ added 'period_notify_ovulation' to user_settings")
            except Exception as e:
                print("⚠ 'period_notify_ovulation' could not be added or already exists:", e)

            # Add columns to period_notification_log
            try:
                db.session.execute(text("ALTER TABLE period_notification_log ADD COLUMN notify_type VARCHAR(20) DEFAULT 'period'"))
                print("✅ added 'notify_type' to period_notification_log")
            except Exception as e:
                print("⚠ 'notify_type' could not be added or already exists:", e)

            db.session.commit()
            print("🚀 Successfully migrated period notification settings.")

        except Exception as e:
            print("❌ Migration Failed:", e)
            db.session.rollback()

if __name__ == '__main__':
    add_columns_to_tables()
