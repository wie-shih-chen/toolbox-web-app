
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app.db')

if not os.path.exists(DB_PATH):
    print(f"Database not found at {DB_PATH}, skipping migration.")
    exit(0)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Helper to check if column exists
def column_exists(table, col):
    cursor.execute(f"PRAGMA table_info({table})")
    cols = [info[1] for info in cursor.fetchall()]
    return col in cols

TABLE = 'user_settings'

# Add editable_month_range
if not column_exists(TABLE, 'editable_month_range'):
    print("Adding editable_month_range...")
    cursor.execute(f"ALTER TABLE {TABLE} ADD COLUMN editable_month_range INTEGER DEFAULT 1")

# Add default_start_time
if not column_exists(TABLE, 'default_start_time'):
    print("Adding default_start_time...")
    cursor.execute(f"ALTER TABLE {TABLE} ADD COLUMN default_start_time VARCHAR(5) DEFAULT '09:00'")

# Add default_end_time
if not column_exists(TABLE, 'default_end_time'):
    print("Adding default_end_time...")
    cursor.execute(f"ALTER TABLE {TABLE} ADD COLUMN default_end_time VARCHAR(5) DEFAULT '18:00'")

# Add target_income
if not column_exists(TABLE, 'target_income'):
    print("Adding target_income...")
    cursor.execute(f"ALTER TABLE {TABLE} ADD COLUMN target_income INTEGER DEFAULT 0")

# Add budget_alert_threshold
if not column_exists(TABLE, 'budget_alert_threshold'):
    print("Adding budget_alert_threshold...")
    cursor.execute(f"ALTER TABLE {TABLE} ADD COLUMN budget_alert_threshold INTEGER DEFAULT 80")

conn.commit()
conn.close()
print("Migration completed.")
