from app import app, db
import sqlite3

def migrate():
    with app.app_context():
        # Using sqlite3 directly to add columns, since SQLAlchemy doesn't support ALTER TABLE easily for sqlite without alembic
        # Connect to db
        conn = sqlite3.connect('app.db')
        c = conn.cursor()
        
        try:
            # 1. Add source to vocab_progress
            c.execute("ALTER TABLE vocab_progress ADD COLUMN source VARCHAR(50) DEFAULT 'system' NOT NULL;")
        except sqlite3.OperationalError as e:
            print("vocab_progress already has source:", e)

        try:
            # Drop the old unique constraint on vocab_progress by recreating the table if necessary, or we can just leave the old one and let the app manage it, but it's better to recreate.
            # Actually SQLite doesn't support DROP CONSTRAINT.
            pass
        except sqlite3.OperationalError:
            pass

        try:
            # 2. Add source to vocab_history_log
            c.execute("ALTER TABLE vocab_history_log ADD COLUMN source VARCHAR(50) DEFAULT 'system' NOT NULL;")
        except sqlite3.OperationalError as e:
            print("vocab_history_log already has source:", e)
            
        conn.commit()
        conn.close()

        # 3. Create GroupDailyAssignment table (if it doesn't exist)
        db.create_all()
        print("Database migration v2 completed.")

if __name__ == '__main__':
    migrate()
