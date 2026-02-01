import os
import sys

# Add parent directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from app import app, db
from models import ReportLog

with app.app_context():
    print("Creating all database tables...")
    db.create_all()
    print("Done! Database tables should be ready.")
    
    # Optional: Verify
    try:
        count = ReportLog.query.count()
        print(f"Verification: ReportLog table access successful (Row count: {count}).")
    except Exception as e:
        print(f"Verification Failed: {e}")
