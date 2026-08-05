import sqlite3
import os

def upgrade():
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app.db')
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute("ALTER TABLE user_settings ADD COLUMN stress_level FLOAT DEFAULT 0.0")
        print("Added stress_level")
    except Exception as e:
        print("stress_level:", e)
        
    try:
        cursor.execute("ALTER TABLE user_settings ADD COLUMN sleep_quality FLOAT DEFAULT 0.5")
        print("Added sleep_quality")
    except Exception as e:
        print("sleep_quality:", e)
        
    try:
        cursor.execute("ALTER TABLE user_settings ADD COLUMN anxiety_multiplier FLOAT DEFAULT 0.0")
        print("Added anxiety_multiplier")
    except Exception as e:
        print("anxiety_multiplier:", e)
        
    conn.commit()
    conn.close()

if __name__ == '__main__':
    upgrade()
