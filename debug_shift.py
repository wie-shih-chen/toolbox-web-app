import logging
import sys
from app import app
from models import db, User, Company, SalaryRecord, CompanyShiftReminder, ShiftReminderLog
from datetime import datetime, timedelta
from services.notification_scheduler import _send_shift_reminders

logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)

with app.app_context():
    now = datetime.utcnow() + timedelta(hours=8)
    print("Simulated TW Time:", now)
    
    # Check if there are any real shifts today/tomorrow
    today_str = now.strftime('%Y-%m-%d')
    tomorrow_str = (now + timedelta(days=1)).strftime('%Y-%m-%d')
    
    shifts = SalaryRecord.query.filter(
        SalaryRecord.type == 'shift',
        SalaryRecord.date.in_([today_str, tomorrow_str])
    ).all()
    print("Found shifts:", len(shifts))
    
    for s in shifts:
        print(f"Shift ID {s.id} on {s.date} {s.start_time} for Company {s.company_id}")
        reminders = CompanyShiftReminder.query.filter_by(company_id=s.company_id, is_active=True).all()
        for r in reminders:
            try:
                dt = datetime.strptime(f"{s.date} {s.start_time}", "%Y-%m-%d %H:%M")
                notify_dt = dt + timedelta(minutes=r.offset_minutes)
                print(f"  Reminder ID {r.id}: offset {r.offset_minutes}m, notify_dt {notify_dt}")
                if now >= notify_dt and now <= notify_dt + timedelta(minutes=15):
                    print("  => SHOULD SEND NOW!")
                    log = ShiftReminderLog.query.filter_by(shift_id=s.id, reminder_id=r.id).first()
                    if log:
                        print("     BUT log exists:", log.sent_at)
                    else:
                        print("     AND log DOES NOT exist!")
            except Exception as e:
                print("  Error:", e)
