from app import app
from models import db
import sqlite3

with app.app_context():
    db.create_all()

try:
    conn = sqlite3.connect('app.db')
    c = conn.cursor()
    c.execute("ALTER TABLE user_settings ADD COLUMN vocab_daily_goal INTEGER DEFAULT 20;")
    conn.commit()
    conn.close()
    print("Added vocab_daily_goal column to user_settings")
except Exception as e:
    print("Column might already exist or error:", e)

