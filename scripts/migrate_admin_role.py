import sqlite3
import os

def migrate():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(base_dir, 'app.db')
    
    if not os.path.exists(db_path):
        print(f"Database {db_path} does not exist yet. No migration needed.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("ALTER TABLE user ADD COLUMN role VARCHAR(10) DEFAULT 'member'")
        print("Added 'role' column to 'user' table.")
    except sqlite3.OperationalError as e:
        print(f"Role column error (might already exist): {e}")

    try:
        cursor.execute("ALTER TABLE user ADD COLUMN can_mark_paid BOOLEAN DEFAULT 0")
        print("Added 'can_mark_paid' column to 'user' table.")
    except sqlite3.OperationalError as e:
        print(f"can_mark_paid column error (might already exist): {e}")

    conn.commit()
    conn.close()
    print("Migration finished.")

if __name__ == '__main__':
    migrate()
