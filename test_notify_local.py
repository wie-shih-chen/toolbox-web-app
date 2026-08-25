import logging
import sys
from app import app
from services.notification_scheduler import _send_shift_reminders
from models import db, User, Company, SalaryRecord, CompanyShiftReminder
from datetime import datetime, timedelta

# Setup logging to stdout
logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)

with app.app_context():
    now = datetime.utcnow() + timedelta(hours=8)
    today_str = now.strftime('%Y-%m-%d')
    current_time_str = now.strftime('%H:%M')

    # Create dummy data for testing
    u = User(username="test_notify_user", password_hash="dummy")
    db.session.add(u)
    db.session.commit()
    
    c = Company(user_id=u.id, name="Test Company", is_active=True)
    db.session.add(c)
    db.session.commit()
    
    # Create shift 5 minutes from now
    shift_time = (now + timedelta(minutes=5)).strftime('%H:%M')
    s = SalaryRecord(user_id=u.id, company_id=c.id, date=today_str, type='shift', start_time=shift_time)
    db.session.add(s)
    
    # Create reminder 5 minutes before (so notify_dt is NOW)
    r = CompanyShiftReminder(company_id=c.id, offset_minutes=-5, message_template="TEST", is_active=True)
    db.session.add(r)
    db.session.commit()
    
    print("Running _send_shift_reminders...")
    try:
        _send_shift_reminders(app)
        print("Success! No exceptions.")
    except Exception as e:
        print(f"Exception caught: {e}")
        
    # Cleanup
    db.session.delete(r)
    db.session.delete(s)
    db.session.delete(c)
    db.session.delete(u)
    db.session.commit()
