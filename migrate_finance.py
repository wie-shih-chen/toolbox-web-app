import sys
import os

# Setup Flask app context
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app import app
from models import db
from sqlalchemy import text

def run_migration():
    with app.app_context():
        print("Running database migrations for finance settings...")
        columns = [
            ("initial_assets", "FLOAT DEFAULT 0.0"),
            ("target_savings_rate", "FLOAT DEFAULT 20.0"),
            ("finance_cycle_type", "VARCHAR(20) DEFAULT 'month'")
        ]
        
        for col, col_type in columns:
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
