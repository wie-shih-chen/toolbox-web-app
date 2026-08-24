"""
Migration: Add Company table and company_id to SalaryRecord
Run: PYTHONPATH=. python3 scripts/maintenance/migrate_companies_v1.py
"""
from app import app
from models import db
from sqlalchemy import text, inspect

def migrate():
    with app.app_context():
        inspector = inspect(db.engine)
        existing_tables = inspector.get_table_names()

        # 1. Create company table if not exists
        if 'company' not in existing_tables:
            print("Creating 'company' table...")
            db.session.execute(text("""
                CREATE TABLE company (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL REFERENCES user(id),
                    name VARCHAR(100) NOT NULL,
                    color VARCHAR(10) DEFAULT '#6366f1',
                    hourly_rate FLOAT DEFAULT 183.0,
                    notify_payday_enabled BOOLEAN DEFAULT 0,
                    notify_payday_day INTEGER DEFAULT 10,
                    notify_payday_time VARCHAR(5) DEFAULT '09:00',
                    notify_weekly_enabled BOOLEAN DEFAULT 0,
                    notify_weekly_day VARCHAR(10) DEFAULT 'sunday',
                    notify_weekly_time VARCHAR(5) DEFAULT '20:00',
                    is_active BOOLEAN DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))
            db.session.commit()
            print("  ✓ 'company' table created.")
        else:
            print("  ✓ 'company' table already exists, skipping.")

        # 2. Add company_id to salary_record if not exists
        salary_cols = [c['name'] for c in inspector.get_columns('salary_record')]
        if 'company_id' not in salary_cols:
            print("Adding 'company_id' column to 'salary_record'...")
            db.session.execute(text(
                "ALTER TABLE salary_record ADD COLUMN company_id INTEGER REFERENCES company(id)"
            ))
            db.session.commit()
            print("  ✓ 'company_id' column added.")
        else:
            print("  ✓ 'company_id' already exists, skipping.")

        print("\nMigration complete!")
        print("NOTE: Existing salary records have company_id = NULL.")
        print("      The app will prompt users to assign them the first time they visit.")

if __name__ == '__main__':
    migrate()
