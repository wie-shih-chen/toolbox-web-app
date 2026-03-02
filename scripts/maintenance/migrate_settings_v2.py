"""
【狀態】已執行過，通常不需要再跑。

【使用時機】
  從不含下列欄位的舊版升級時執行。
  新增欄位：user_settings 資料表
    - billing_cycle_start_day  帳單週期起始日
    - custom_categories        自訂記帳類別（JSON）
    - recurring_expenses       固定支出（JSON）

【執行方式】
  cd ~/toolbox-web-app
  python scripts/maintenance/migrate_settings_v2.py

【依賴】
  純 sqlite3，不需要 Flask 虛擬環境套件。
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'app.db')

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        try:
            cursor.execute("ALTER TABLE user_settings ADD COLUMN billing_cycle_start_day INTEGER DEFAULT 10")
            print("Added billing_cycle_start_day")
        except sqlite3.OperationalError:
            print("billing_cycle_start_day already exists")

        try:
            cursor.execute("ALTER TABLE user_settings ADD COLUMN custom_categories TEXT DEFAULT '[]'")
            print("Added custom_categories")
        except sqlite3.OperationalError:
            print("custom_categories already exists")

        try:
            cursor.execute("ALTER TABLE user_settings ADD COLUMN recurring_expenses TEXT DEFAULT '[]'")
            print("Added recurring_expenses")
        except sqlite3.OperationalError:
            print("recurring_expenses already exists")

        conn.commit()
        print("Migration V2 completed successfully!")

    except Exception as e:
        print(f"Migration failed: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
