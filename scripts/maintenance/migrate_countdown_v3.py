import sqlite3
import os

def migrate_v3():
    """Adds notify_enabled column to Countdown table and creates CountdownSubEvent table"""
    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../app.db'))
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found at {db_path}")
        return
        
    print(f"Using database: {db_path}")
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. Add notify_enabled to countdown table
        cursor.execute("PRAGMA table_info(countdown)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if 'notify_enabled' not in columns:
            print("Adding `notify_enabled` column to `countdown` table...")
            cursor.execute("ALTER TABLE countdown ADD COLUMN notify_enabled BOOLEAN DEFAULT 1;")
            print("✅ Successfully added `notify_enabled` column!")
        else:
            print("ℹ️ Column `notify_enabled` already exists in `countdown`.")
            
        # 2. Create countdown_sub_event table
        print("Ensuring `countdown_sub_event` table exists...")
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS countdown_sub_event (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            countdown_id INTEGER NOT NULL,
            title VARCHAR(100) NOT NULL,
            target_date VARCHAR(10) NOT NULL,
            icon VARCHAR(10) DEFAULT '📅',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (countdown_id) REFERENCES countdown(id) ON DELETE CASCADE
        );
        """
        cursor.execute(create_table_sql)
        print("✅ Successfully verified/created `countdown_sub_event` table!")

        conn.commit()
    except Exception as e:
        print(f"❌ Error during migration: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    migrate_v3()
    print("✅ Migration complete. Exiting...")
