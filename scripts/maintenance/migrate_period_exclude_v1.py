import sqlite3
import os

def migrate():
    # Base directory of the web_app
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    db_path = os.path.join(base_dir, 'app.db')
    
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    print(f"Migrating database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if the column already exists
        cursor.execute("PRAGMA table_info(period_record)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'exclude_from_avg' not in columns:
            print("Adding 'exclude_from_avg' column to 'period_record' table...")
            cursor.execute("ALTER TABLE period_record ADD COLUMN exclude_from_avg BOOLEAN DEFAULT 0")
            print("Migration successful.")
        else:
            print("'exclude_from_avg' column already exists.")

        conn.commit()
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
