import sqlite3

db_path = 'app.db'
print(f"Connecting to {db_path}...")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 1. Add columns to user_settings
columns_to_add = [
    ("enable_finance_tracking", "BOOLEAN DEFAULT 0"),
    ("insurance_salary", "FLOAT DEFAULT 0.0"),
    ("health_insurance_dependents", "INTEGER DEFAULT 0"),
    ("labor_pension_rate", "FLOAT DEFAULT 0.0")
]

for col_name, col_type in columns_to_add:
    try:
        print(f"Adding {col_name}...")
        cursor.execute(f"ALTER TABLE user_settings ADD COLUMN {col_name} {col_type}")
        print(f"Added {col_name} successfully.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print(f"Column {col_name} already exists. Skipping.")
        else:
            print(f"Error adding {col_name}: {e}")

# 2. Create savings_goal table
try:
    print("Creating savings_goal table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS savings_goal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title VARCHAR(100) NOT NULL,
            target_amount FLOAT NOT NULL,
            current_amount FLOAT DEFAULT 0.0,
            target_date VARCHAR(10),
            icon VARCHAR(10) DEFAULT '💰',
            is_active BOOLEAN DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES user(id)
        )
    """)
    print("Created savings_goal table successfully.")
except Exception as e:
    print(f"Error creating savings_goal table: {e}")

conn.commit()
conn.close()
print("Migration completed.")
