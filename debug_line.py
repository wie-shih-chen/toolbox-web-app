import logging
import sys
from app import app
from models import db, User, Company, SalaryRecord, CompanyShiftReminder, ShiftReminderLog, UserSettings, LineBinding
from datetime import datetime, timedelta
from services.notification_scheduler import _send_shift_reminders

logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)

with app.app_context():
    now = datetime.utcnow() + timedelta(hours=8)
    today_str = now.strftime('%Y-%m-%d')
    
    # Create dummy data
    u = User(username="test_line_user", password_hash="dummy")
    db.session.add(u)
    db.session.commit()
    
    settings = UserSettings(user_id=u.id, notification_methods='["line"]')
    db.session.add(settings)
    
    # Create LineBinding so it simulates a bound LINE account
    binding = LineBinding(user_id=u.id, line_user_id="dummy_line_id", nickname="test", permissions='["salary"]')
    db.session.add(binding)
    
    c = Company(user_id=u.id, name="Test Company", is_active=True)
    db.session.add(c)
    db.session.commit()
    
    # Shift 5 mins from now
    shift_time = (now + timedelta(minutes=5)).strftime('%H:%M')
    s = SalaryRecord(user_id=u.id, company_id=c.id, date=today_str, type='shift', start_time=shift_time)
    db.session.add(s)
    
    # Reminder 5 mins before
    r = CompanyShiftReminder(company_id=c.id, offset_minutes=-5, message_template="TEST", is_active=True)
    db.session.add(r)
    db.session.commit()
    
    print("Testing Line send...")
    _send_shift_reminders(app)
    
    log = ShiftReminderLog.query.filter_by(shift_id=s.id, reminder_id=r.id).first()
    if log:
        print("Log created successfully at", log.sent_at)
    else:
        print("Failed to create log!")
        
    db.session.delete(r)
    db.session.delete(s)
    db.session.delete(c)
    db.session.delete(binding)
    db.session.delete(settings)
    db.session.delete(u)
    db.session.commit()
