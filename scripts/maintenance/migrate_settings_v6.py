from app import app
from models import db
from sqlalchemy import text

def migrate():
    with app.app_context():
        # Check if column exists
        inspector = db.inspect(db.engine)
        columns = [c['name'] for c in inspector.get_columns('user_settings')]
        
        if 'asset_tracking_start_date' not in columns:
            print("Adding asset_tracking_start_date to user_settings...")
            db.session.execute(text('ALTER TABLE user_settings ADD COLUMN asset_tracking_start_date VARCHAR(10)'))
            db.session.commit()
            print("Migration successful.")
        else:
            print("Column asset_tracking_start_date already exists.")

if __name__ == '__main__':
    migrate()
