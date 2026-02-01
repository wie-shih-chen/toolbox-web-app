from models import db, ReportLog
from services.salary_service import SalaryService
from services.expense_service import ExpenseService
from services.email_service import EmailService
from datetime import datetime, timedelta
import threading
from flask import current_app

class ReportService:
    @staticmethod
    def get_billing_period(target_date=None):
        """
        Calculate the LAST COMPLETED billing period relative to target_date.
        Cycle: 10th to 10th.
        Triggers on 11th.
        """
        if target_date is None:
            target_date = datetime.now()
            
        # Example 1: Today is Feb 11. 
        # We want period ending Feb 10 (Yesterday).
        # Trigger condition: Day >= 11.
        
        # Example 2: Today is Feb 15.
        # We want period ending Feb 10.
        
        # Example 3: Today is Feb 9.
        # We want period ending Jan 10. (Because Feb 10 hasn't happened yet)
        
        if target_date.day >= 11:
            # Current month's 10th is the end date
            end_date = datetime(target_date.year, target_date.month, 10)
        else:
            # Previous month's 10th is the end date
            # Handle Jan case
            month = target_date.month - 1
            year = target_date.year
            if month < 1:
                month = 12
                year -= 1
            end_date = datetime(year, month, 10)
            
        # Start date is ~1 month before end date
        # Logic: Go back 20 days from end_date (to prev month) then set day to 10
        prev_month_date = end_date - timedelta(days=20)
        start_date = datetime(prev_month_date.year, prev_month_date.month, 10)
        
        return start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')

    @staticmethod
    def check_and_send_pending_reports(user):
        """
        Checks if the report for the latest period has been sent to this user.
        If not, sends it.
        Uses threading to avoid blocking the request.
        """
        if not user.is_authenticated:
            return
            
        start_date, end_date = ReportService.get_billing_period()
        
        # Check if already logged
        log_exist = ReportLog.query.filter_by(
            user_id=user.id,
            period_start=start_date,
            period_end=end_date
        ).first()
        
        if log_exist:
            return # Already sent
            
        # Pass user_id instead of user object to avoid threading context issues
        user_id = user.id
        
        report_thread = threading.Thread(
            target=ReportService._generate_and_send,
            args=(current_app._get_current_object(), user_id, start_date, end_date)
        )
        report_thread.start()
        
    @staticmethod
    def _generate_and_send(app, user_id, start_date, end_date):
        with app.app_context():
            # Re-fetch user inside the thread's context
            user = User.query.get(user_id)
            if not user or not user.email:
                return
            
            # --- Salary Report ---
            try:
                salary_service = SalaryService()
                records = salary_service.get_records_by_range(start_date, end_date, user=user)
                if records:
                    records.sort(key=lambda x: x['date'], reverse=True)
                    total_salary = sum(r.get('amount', 0) for r in records)
                    
                    EmailService.send_email(
                        to=user.email,
                        subject=f'每月薪資報表 ({start_date} ~ {end_date})',
                        template='email/salary_export.html',
                        username=user.username,
                        record_count=len(records),
                        export_date=datetime.now().strftime('%Y/%m/%d'),
                        total_amount=f"${total_salary:,}",
                        records=records
                    )
                    
                    # Log it (Partial log not perfect, but we log the 'attempt' as done if at least one succeeds or both?)
                    # Let's log 'salary' type
                    db.session.add(ReportLog(
                        user_id=user.id,
                        period_start=start_date,
                        period_end=end_date,
                        report_type='salary',
                        sent_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    ))
            except Exception as e:
                print(f"Error sending salary report: {e}")

            # --- Expense Report ---
            try:
                expense_service = ExpenseService()
                data = expense_service.get_summary(start_date, end_date, user=user)
                records = data['records']
                if records:
                     category_stats = data['category_split']
                     top_categories = sorted(category_stats.items(), key=lambda x: x[1], reverse=True)[:5]
                     
                     EmailService.send_email(
                        to=user.email,
                        subject=f'每月記帳報表 ({start_date} ~ {end_date})',
                        template='email/expense_export.html',
                        username=user.username,
                        period=f"{start_date} ~ {end_date}",
                        total_amount=f"${data.get('total_amount', 0):,}",
                        records=records,
                        top_categories=top_categories
                    )
                     
                     db.session.add(ReportLog(
                        user_id=user.id,
                        period_start=start_date,
                        period_end=end_date,
                        report_type='expense',
                        sent_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    ))
            except Exception as e:
                print(f"Error sending expense report: {e}")
                
            db.session.commit()
