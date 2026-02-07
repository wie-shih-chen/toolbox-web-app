import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from models import UserSettings
from sqlalchemy import text

def migrate():
    with app.app_context():
        print("Starting migration v5: Add LINE Bot fields...")
        
        # Check if columns exist
        inspector = db.inspect(db.engine)
        columns = [c['name'] for c in inspector.get_columns('user_settings')]
        
        try:
            with db.engine.connect() as conn:
                if 'line_user_id' not in columns:
                    print("Adding line_user_id...")
                    conn.execute(text("ALTER TABLE user_settings ADD COLUMN line_user_id VARCHAR(255)"))
                
                if 'binding_code' not in columns:
                    print("Adding binding_code...")
                    conn.execute(text("ALTER TABLE user_settings ADD COLUMN binding_code VARCHAR(6)"))
                
                if 'binding_expiry' not in columns:
                    print("Adding binding_expiry...")
                    conn.execute(text("ALTER TABLE user_settings ADD COLUMN binding_expiry DATETIME"))
                
                if 'notification_methods' not in columns:
                    print("Adding notification_methods...")
                    conn.execute(text("ALTER TABLE user_settings ADD COLUMN notification_methods TEXT DEFAULT '[\"email\"]'"))
                
                conn.commit()
                
            print("Migration v5 completed successfully!")
            
        except Exception as e:
            print(f"Migration failed: {e}")

if __name__ == "__main__":
    migrate()
