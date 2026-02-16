import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from models import db, UserSettings

# context is needed
with app.app_context():
    try:
        settings = UserSettings.query.all()
        print(f"Found {len(settings)} user settings to reset.")
        
        for s in settings:
            s.custom_categories = '[]'
            s.recurring_expenses = '[]'
            s.quick_shortcuts = '[]'
            print(f"Reset settings for User ID: {s.user_id}")
            
        db.session.commit()
        print("All settings reset to defaults successfully.")
        
    except Exception as e:
        db.session.rollback()
        print(f"Error resetting settings: {e}")
