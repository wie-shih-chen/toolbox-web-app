import sqlite3
import os
import sys

# Ensure app context can be loaded
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from app import app, db
from models import Countdown

def migrate_v2():
    """Adds image_path column to Countdown table"""
    db_path = os.path.join(app.root_path, 'instance', 'toolbox.db')
    
    # Let's use raw SQL since SQLite alter table is easiest this way
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if column exists
        cursor.execute("PRAGMA table_info(countdown)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if 'image_path' not in columns:
            print("Adding `image_path` column to `countdown` table...")
            cursor.execute("ALTER TABLE countdown ADD COLUMN image_path VARCHAR(255) NULL;")
            conn.commit()
            print("✅ Successfully added `image_path` column!")
        else:
            print("ℹ️ Column `image_path` already exists.")
            
    except Exception as e:
        print(f"❌ Error during migration: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    with app.app_context():
        migrate_v2()
