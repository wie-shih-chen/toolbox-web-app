import logging
import sys
from app import app
from models import db, User, Company, SalaryRecord, CompanyShiftReminder, ShiftReminderLog, UserSettings, LineBinding
from datetime import datetime, timedelta
import json
from services.notification_service import NotificationService
from services.line_service import LineService

logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)

with app.app_context():
    now = datetime.utcnow() + timedelta(hours=8)
    today_str = now.strftime('%Y-%m-%d')
    
    u = User(username="test_user2", password_hash="dummy")
    db.session.add(u)
    db.session.commit()
    
    settings = UserSettings(user_id=u.id, notification_methods='["line"]')
    db.session.add(settings)
    
    binding = LineBinding(user_id=u.id, line_user_id="dummy_line_id", nickname="test", permissions='["salary"]')
    db.session.add(binding)
    db.session.commit()
    
    print("Direct push_to_user:")
    res = LineService.push_to_user(u.id, "Hello", module='salary')
    print("Result:", res)
    
    print("NotificationService:")
    success = NotificationService.send_notification(u, "Test", "Msg", ['line'], 'salary')
    print("Success:", success)
    
    db.session.delete(binding)
    db.session.delete(settings)
    db.session.delete(u)
    db.session.commit()
