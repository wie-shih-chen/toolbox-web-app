import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from models import User
from sqlalchemy import text

def migrate():
    with app.app_context():
        # Check if columns exist
        with db.engine.connect() as conn:
            columns = conn.execute(text("PRAGMA table_info(user)")).fetchall()
            col_names = [col[1] for col in columns]
            
            if 'avatar_type' not in col_names:
                print("Adding avatar_type column...")
                conn.execute(text("ALTER TABLE user ADD COLUMN avatar_type TEXT DEFAULT 'preset'"))
                
            if 'avatar_val' not in col_names:
                print("Adding avatar_val column...")
                conn.execute(text("ALTER TABLE user ADD COLUMN avatar_val TEXT DEFAULT 'default'"))
                
            conn.commit()
            print("Migration completed.")

if __name__ == '__main__':
    migrate()
