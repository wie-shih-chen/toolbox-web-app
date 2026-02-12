
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'app.db')

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Add billing_cycle_start_day
        try:
            cursor.execute("ALTER TABLE user_settings ADD COLUMN billing_cycle_start_day INTEGER DEFAULT 10")
            print("Added billing_cycle_start_day")
        except sqlite3.OperationalError:
            print("billing_cycle_start_day already exists")

        # Add custom_categories
        try:
            cursor.execute("ALTER TABLE user_settings ADD COLUMN custom_categories TEXT DEFAULT '[]'")
            print("Added custom_categories")
        except sqlite3.OperationalError:
            print("custom_categories already exists")

        # Add recurring_expenses
        try:
            cursor.execute("ALTER TABLE user_settings ADD COLUMN recurring_expenses TEXT DEFAULT '[]'")
            print("Added recurring_expenses")
        except sqlite3.OperationalError:
            print("recurring_expenses already exists")

        conn.commit()
        print("Migration V2 completed successfully!")

    except Exception as e:
        print(f"Migration failed: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
