from app import app, db
from sqlalchemy import text

def migrate():
    with app.app_context():
        print("Starting migration...")
        try:
            # Check if column exists
            with db.engine.connect() as conn:
                result = conn.execute(text("PRAGMA table_info(user)"))
                columns = [row[1] for row in result]
                
                if 'email' not in columns:
                    print("Adding 'email' column to 'user' table...")
                    conn.execute(text("ALTER TABLE user ADD COLUMN email VARCHAR(120)"))
                    # Add unique index if possible, but SQLite limits ALTER TABLE capabilities.
                    # We will rely on app logic for uniqueness for now, or recreate table if strictly needed.
                    # For a simple 'add column', this usually works.
                    conn.commit()
                    print("Migration successful: Added 'email' column.")
                else:
                    print("Column 'email' already exists.")
                    
        except Exception as e:
            print(f"Migration failed: {e}")

if __name__ == "__main__":
    migrate()
