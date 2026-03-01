"""
Migration: Create calendar_notification_log table.
Run once on the server after deploying the new code:

    python scripts/migrate_calendar_notify_log.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

from app import app
from models import db

with app.app_context():
    db.create_all()
    print("✅ calendar_notification_log table ensured.")
