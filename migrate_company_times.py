import sys
import os

# Setup Flask app context
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app import app
from models import db
from sqlalchemy import text

def run_migration():
    with app.app_context():
        print("Running database migrations for company default times...")
        try:
            db.session.execute(text("ALTER TABLE company ADD COLUMN default_start_time VARCHAR(5) DEFAULT '';"))
            print("Successfully added default_start_time column.")
        except Exception as e:
            if "duplicate column name" in str(e).lower():
                print("Column default_start_time already exists, skipping.")
            else:
                print(f"Error adding default_start_time: {e}")

        try:
            db.session.execute(text("ALTER TABLE company ADD COLUMN default_end_time VARCHAR(5) DEFAULT '';"))
            print("Successfully added default_end_time column.")
        except Exception as e:
            if "duplicate column name" in str(e).lower():
                print("Column default_end_time already exists, skipping.")
            else:
                print(f"Error adding default_end_time: {e}")
                
        db.session.commit()
        print("Migration complete!")

if __name__ == '__main__':
    run_migration()
