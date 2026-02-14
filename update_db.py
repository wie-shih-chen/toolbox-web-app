import sqlite3
import os

# Define the database path
# On PythonAnywhere or typical deployment, it might be in the same directory
db_path = 'app.db'

print(f"Checking database at: {os.path.abspath(db_path)}")

if not os.path.exists(db_path):
    print(f"Error: Database not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
c = conn.cursor()

# Check if 'reminder' table exists
try:
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='reminder';")
    if not c.fetchone():
        print("Error: Table 'reminder' not found!")
        exit(1)
        
    # Check columns
    c.execute("PRAGMA table_info(reminder);")
    columns = [row[1] for row in c.fetchall()]
    print(f"Current columns in 'reminder': {columns}")
    
    if 'weekdays' not in columns:
        print("Adding 'weekdays' column...")
        try:
            c.execute("ALTER TABLE reminder ADD COLUMN weekdays VARCHAR(50)")
            conn.commit()
            print("Success: 'weekdays' column added.")
        except Exception as e:
            print(f"Error adding column: {e}")
    else:
        print("Info: 'weekdays' column already exists. No action needed.")

except Exception as e:
    print(f"An unexpected error occurred: {e}")
finally:
    conn.close()
