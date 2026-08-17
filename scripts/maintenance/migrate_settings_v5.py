"""
【狀態】新建

【使用時機】
  新增欄位：
    - enable_monthly_savings BOOLEAN DEFAULT 0
    - monthly_savings_amount INTEGER DEFAULT 0

【執行方式】
  cd ~/toolbox-web-app
  python scripts/maintenance/migrate_settings_v5.py
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'app.db')

def migrate():
    print(f"Migrating database at {DB_PATH}")
    if not os.path.exists(DB_PATH):
        print("Database not found!")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute("PRAGMA table_info(user_settings)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if 'enable_monthly_savings' not in columns:
            print("Adding 'enable_monthly_savings' column...")
            cursor.execute("ALTER TABLE user_settings ADD COLUMN enable_monthly_savings BOOLEAN DEFAULT 0")
        else:
            print("Column 'enable_monthly_savings' already exists.")
            
        if 'monthly_savings_amount' not in columns:
            print("Adding 'monthly_savings_amount' column...")
            cursor.execute("ALTER TABLE user_settings ADD COLUMN monthly_savings_amount INTEGER DEFAULT 0")
        else:
            print("Column 'monthly_savings_amount' already exists.")
            
        conn.commit()
        print("Migration V5 completed successfully.")
    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
