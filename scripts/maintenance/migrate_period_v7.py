import os
import sqlite3
import sys

# Add parent directory to path to import app config
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def migrate():
    """
    【使用時機】新增「生理期追蹤器」功能時執行。
    【方法】cd /Users/weishichen/Documents/程式/python/工具箱/web_app && python scripts/maintenance/migrate_period_v7.py
    【說明】
    1. 在 user_settings 資料表中新增 avg_period_cycle (整數，預設28) 與 avg_period_duration (整數，預設5)。
    2. 建立全新的 period_record 資料表以儲存經期歷史。
    """
    root_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    db_path = os.path.join(root_path, 'app.db')
    print(f"📂 DB: {db_path}")

    if not os.path.exists(db_path):
        print("❌ app.db does not exist.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Create PeriodRecord table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS period_record (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                start_date VARCHAR(10) NOT NULL,
                end_date VARCHAR(10),
                cycle_length INTEGER,
                note VARCHAR(255),
                created_at DATETIME,
                FOREIGN KEY(user_id) REFERENCES user(id)
            )
        ''')
        print("✅ Executed CREATE TABLE for period_record.")
        
        # Add new fields to user_settings
        try:
            cursor.execute('ALTER TABLE user_settings ADD COLUMN avg_period_cycle INTEGER DEFAULT 28')
            print("✅ Added 'avg_period_cycle' column to user_settings.")
        except sqlite3.OperationalError as e:
            if 'duplicate column' in str(e).lower():
                print("⚠️ Column 'avg_period_cycle' already exists. Skipping.")
            else:
                raise e

        try:
            cursor.execute('ALTER TABLE user_settings ADD COLUMN avg_period_duration INTEGER DEFAULT 5')
            print("✅ Added 'avg_period_duration' column to user_settings.")
        except sqlite3.OperationalError as e:
            if 'duplicate column' in str(e).lower():
                print("⚠️ Column 'avg_period_duration' already exists. Skipping.")
            else:
                raise e
        
        # We need to set defaults for existing rows if columns were just added
        cursor.execute('UPDATE user_settings SET avg_period_cycle = 28 WHERE avg_period_cycle IS NULL')
        cursor.execute('UPDATE user_settings SET avg_period_duration = 5 WHERE avg_period_duration IS NULL')

        conn.commit()
        print("🚀 Successfully marked database schema for Menstrual Cycle Tracker (v7).")

    except Exception as e:
        print(f"❌ Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
