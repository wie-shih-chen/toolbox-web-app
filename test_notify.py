from services.notification_scheduler import _send_shift_reminders, _send_company_notifications
from models import ShiftReminderLog, CompanyShiftReminder, Company, SalaryRecord, db
from datetime import datetime, timedelta

now = datetime.utcnow() + timedelta(hours=8)
print("Current TW Time:", now)

# Let's see active reminders
reminders = CompanyShiftReminder.query.filter_by(is_active=True).all()
print("Active Reminders:", len(reminders))
for r in reminders:
    print(f"  ID {r.id}: company {r.company_id}, offset {r.offset_minutes}")

# Let's see shifts for today/tomorrow
today_str = now.strftime('%Y-%m-%d')
tomorrow_str = (now + timedelta(days=1)).strftime('%Y-%m-%d')
shifts = SalaryRecord.query.filter(
    SalaryRecord.type == 'shift',
    SalaryRecord.date.in_([today_str, tomorrow_str])
).all()
print("Shifts today/tomorrow:", len(shifts))
for s in shifts:
    print(f"  Shift {s.id}: company {s.company_id}, {s.date} {s.start_time}")

print("Testing _send_shift_reminders...")
_send_shift_reminders(app)

print("ShiftReminderLog count:", ShiftReminderLog.query.count())
logs = ShiftReminderLog.query.order_by(ShiftReminderLog.sent_at.desc()).limit(5).all()
for l in logs:
    print(f"  Log {l.id}: shift {l.shift_id}, reminder {l.reminder_id}, sent_at {l.sent_at}")
