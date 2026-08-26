import sys
import os

# Setup Flask app context
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app import app
from models import db
from sqlalchemy import text

def run_migration():
    with app.app_context():
        print("Running database migrations for company overtime setting...")
        try:
            db.session.execute(text("ALTER TABLE company ADD COLUMN enable_overtime BOOLEAN DEFAULT 0;"))
            print("Successfully added enable_overtime column.")
        except Exception as e:
            if "duplicate column name" in str(e).lower():
                print("Column enable_overtime already exists, skipping.")
            else:
                print(f"Error adding enable_overtime: {e}")
                
        db.session.commit()
        print("Migration complete!")

if __name__ == '__main__':
    run_migration()
