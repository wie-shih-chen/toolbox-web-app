import sqlite3
import os

# Get the absolute path to app.db
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
db_path = os.path.join(base_dir, 'app.db')

print(f"Connecting to {db_path}...")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("Creating period_notification_log table...")
cursor.execute("""
CREATE TABLE IF NOT EXISTS period_notification_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    predicted_start_date TEXT NOT NULL,
    sent_date TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES user(id)
)
""")

print("Adding columns to user_settings...")
columns = [
    ("period_notify_enabled", "BOOLEAN DEFAULT 1"),
    ("period_notify_time", "TEXT DEFAULT '08:00'"),
    ("period_notify_days_before", "INTEGER DEFAULT 3")
]

for col_name, col_type in columns:
    try:
        cursor.execute(f"ALTER TABLE user_settings ADD COLUMN {col_name} {col_type}")
        print(f"Column '{col_name}' added.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print(f"Column '{col_name}' already exists.")
        else:
            print(f"Error adding '{col_name}': {e}")

conn.commit()
conn.close()
print("Migration completed successfully!")
