import sys
import os

# Setup Flask app context
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app import app
from models import db
from sqlalchemy import text

def run_migration():
    with app.app_context():
        print("Running database migrations for fixed extra income...")
        col = "fixed_extra_income"
        col_type = "FLOAT DEFAULT 0.0"
        
        try:
            db.session.execute(text(f"ALTER TABLE user_settings ADD COLUMN {col} {col_type};"))
            print(f"Successfully added {col} column.")
        except Exception as e:
            if "duplicate column name" in str(e).lower():
                print(f"Column {col} already exists, skipping.")
            else:
                print(f"Error adding {col}: {e}")
                
        db.session.commit()
        print("Migration complete!")

if __name__ == '__main__':
    run_migration()
