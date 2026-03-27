import sqlite3
import os

db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../app.db'))
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    cursor.execute("PRAGMA table_info(countdown)")
    columns = [info[1] for info in cursor.fetchall()]
    if 'repeat_annually' not in columns:
        cursor.execute("ALTER TABLE countdown ADD COLUMN repeat_annually BOOLEAN DEFAULT 0;")
        print("Added repeat_annually to countdown")
        
    cursor.execute("PRAGMA table_info(countdown_sub_event)")
    columns = [info[1] for info in cursor.fetchall()]
    if 'repeat_annually' not in columns:
        cursor.execute("ALTER TABLE countdown_sub_event ADD COLUMN repeat_annually BOOLEAN DEFAULT 0;")
        print("Added repeat_annually to countdown_sub_event")
        
    conn.commit()
    print("Migration successful")
except Exception as e:
    print(f"Error: {e}")
finally:
    conn.close()
