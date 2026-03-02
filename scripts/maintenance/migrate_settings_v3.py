"""
【狀態】已執行過，通常不需要再跑。

【使用時機】
  若 user_settings 資料表缺少 quick_shortcuts 欄位時執行。
  新增欄位：
    - quick_shortcuts  記帳頁快捷摘要（JSON 陣列）

【執行方式】
  cd ~/toolbox-web-app
  python scripts/maintenance/migrate_settings_v3.py

【依賴】
  純 sqlite3，不需要 Flask 虛擬環境套件。
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
        
        if 'quick_shortcuts' not in columns:
            print("Adding 'quick_shortcuts' column...")
            cursor.execute("ALTER TABLE user_settings ADD COLUMN quick_shortcuts TEXT DEFAULT '[]'")
            print("Column added successfully.")
        else:
            print("Column 'quick_shortcuts' already exists.")
            
        conn.commit()
    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
