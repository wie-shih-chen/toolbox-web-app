import sys
import os

# Setup Flask app context
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app import app
from models import db
from sqlalchemy import text

def run_migration():
    with app.app_context():
        print("Running database migrations for dashboard and dock layout...")
        try:
            db.session.execute(text("ALTER TABLE user_settings ADD COLUMN dashboard_order TEXT DEFAULT '[]';"))
            print("Successfully added dashboard_order column.")
        except Exception as e:
            if "duplicate column name" in str(e).lower():
                print("Column dashboard_order already exists, skipping.")
            else:
                print(f"Error adding dashboard_order: {e}")

        try:
            db.session.execute(text("ALTER TABLE user_settings ADD COLUMN dock_order TEXT DEFAULT '[\"main.index\", \"salary.index\", \"ntut.calendar\", \"expense.today\"]';"))
            print("Successfully added dock_order column.")
        except Exception as e:
            if "duplicate column name" in str(e).lower():
                print("Column dock_order already exists, skipping.")
            else:
                print(f"Error adding dock_order: {e}")
                
        db.session.commit()
        print("Migration complete!")

if __name__ == '__main__':
    run_migration()
