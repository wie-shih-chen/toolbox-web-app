import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import app, db
from sqlalchemy import text

with app.app_context():
    print("Running migration: Finance Tools v1...")
    
    # 1. Add columns to user_settings
    columns_to_add = [
        ("enable_finance_tracking", "BOOLEAN DEFAULT 0"),
        ("insurance_salary", "FLOAT DEFAULT 0.0"),
        ("health_insurance_dependents", "INTEGER DEFAULT 0"),
        ("labor_pension_rate", "FLOAT DEFAULT 0.0")
    ]
    
    with db.engine.connect() as conn:
        for col_name, col_type in columns_to_add:
            try:
                conn.execute(text(f"SELECT {col_name} FROM user_settings LIMIT 1"))
                print(f"Column '{col_name}' already exists. Skipping.")
            except Exception:
                print(f"Adding '{col_name}' column...")
                conn.execute(text(f"ALTER TABLE user_settings ADD COLUMN {col_name} {col_type}"))
                conn.commit()
                print(f"Added '{col_name}' successfully.")

        # 2. Create savings_goal table if not exists
        try:
            conn.execute(text("SELECT id FROM savings_goal LIMIT 1"))
            print("Table 'savings_goal' already exists. Skipping.")
        except Exception:
            print("Creating 'savings_goal' table...")
            conn.execute(text("""
                CREATE TABLE savings_goal (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    title VARCHAR(100) NOT NULL,
                    target_amount FLOAT NOT NULL,
                    current_amount FLOAT DEFAULT 0.0,
                    target_date VARCHAR(10),
                    icon VARCHAR(10) DEFAULT '💰',
                    is_active BOOLEAN DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES user(id)
                )
            """))
            conn.commit()
            print("Created 'savings_goal' table successfully.")

    print("Migration Finance Tools v1 completed.")
