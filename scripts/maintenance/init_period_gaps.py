import os
import sys

# Add the project root to sys.path
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(base_dir)

from app import app
from models import User
from services.period_service import PeriodService

def run_maintenance():
    with app.app_context():
        users = User.query.all()
        print(f"Starting maintenance for {len(users)} users...")
        for user in users:
            print(f"Processing user {user.username} (ID: {user.id})...")
            service = PeriodService(user.id)
            # This will trigger auto-detection of > 60 days cycles and update average
            service._recalculate_all_cycle_lengths()
            print(f"Finished user {user.username}.")
        print("Maintenance complete.")

if __name__ == "__main__":
    run_maintenance()
