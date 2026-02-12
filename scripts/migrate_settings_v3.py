import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app.db')

def migrate():
    print(f"Migrating database at {DB_PATH}")
    if not os.path.exists(DB_PATH):
        print("Database not found!")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Check if column exists
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
