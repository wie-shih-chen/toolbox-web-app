import json
from datetime import datetime
from models import User, UserSettings, ExpenseRecord, db
from services.notification_service import NotificationService, NotificationTemplate

class RecurringFinanceService:
    @staticmethod
    def check_and_create(app):
        """
        Check all users for recurring expenses and incomes that match today's day of the month.
        Create actual records if they haven't been created this month.
        """
        now = datetime.now()
        today_day = now.day
        current_month_prefix = now.strftime('%Y-%m')
        today_date_str = now.strftime('%Y-%m-%d %H:%M:%S')

        users = User.query.all()
        for user in users:
            settings = UserSettings.query.filter_by(user_id=user.id).first()
            if not settings:
                continue

            # Process recurring expenses
            try:
                recurring_expenses = json.loads(settings.recurring_expenses or '[]')
            except:
                recurring_expenses = []

            for rec in recurring_expenses:
                try:
                    target_day = int(rec.get('day', 0))
                except:
                    continue
                
                # If today is the day (or if target_day > 28 and today is the last day of month, handling end of month could be complex, 
                # but let's stick to strict matching for now, or just basic check)
                # To handle months with fewer days:
                import calendar
                last_day_of_month = calendar.monthrange(now.year, now.month)[1]
                effective_day = min(target_day, last_day_of_month)

                if today_day == effective_day:
                    name = rec.get('name', '固定支出')
                    amount = float(rec.get('amount', 0))
                    category = rec.get('category', '其他')
                    
                    # Check if already added this month
                    auto_note = f"[系統自動扣款] {name}"
                    
                    # Query existing records for this month with the exact auto_note
                    already_exists = ExpenseRecord.query.filter(
                        ExpenseRecord.user_id == user.id,
                        ExpenseRecord.timestamp.like(f"{current_month_prefix}%"),
                        ExpenseRecord.note == auto_note
                    ).first()

                    if not already_exists:
                        # Create record
                        new_expense = ExpenseRecord(
                            user_id=user.id,
                            category=category,
                            amount=amount,
                            note=auto_note,
                            timestamp=today_date_str
                        )
                        db.session.add(new_expense)
                        db.session.commit()
                        
                        print(f"[RecurringFinance] User {user.id}: Added {name} (${amount})")
                        
                        # Send Notification
                        msg = NotificationTemplate.get_recurring_expense_msg(name, amount, category)
                        subject = NotificationTemplate.get_recurring_expense_subject(name)
                        NotificationService.send_notification(
                            user=user,
                            subject=subject,
                            message_text=msg,
                            module='expense'
                        )
