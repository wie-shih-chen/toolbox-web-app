from models import db, ReportLog, User
from services.salary_service import SalaryService
from services.expense_service import ExpenseService
from services.email_service import EmailService
from datetime import datetime, timedelta
import threading
import json
from flask import current_app
from services.line_service import LineService

class ReportService:
    @staticmethod
    @staticmethod
    def get_billing_period(target_date=None):
        """
        Calculate the LAST COMPLETED billing period (Standard Month).
        Report triggers on 11th (Pay Day + 1, or generally safe date).
        Period: 1st of previous month - Last day of previous month.
        """
        if target_date is None:
            target_date = datetime.now()
            
        # If today is Feb 11, we report on Jan (Jan 1 - Jan 31).
        
        # Calculate previous month year and month
        first_of_this_month = datetime(target_date.year, target_date.month, 1)
        last_day_prev_month = first_of_this_month - timedelta(days=1)
        first_day_prev_month = datetime(last_day_prev_month.year, last_day_prev_month.month, 1)
        
        return first_day_prev_month.strftime('%Y-%m-%d'), last_day_prev_month.strftime('%Y-%m-%d')

    @staticmethod
    def check_and_send_pending_reports(user):
        """
        Checks if the report for the latest period has been sent to this user.
        If not, sends it.
        Now respects user.settings.monthly_report_day preference.
        """
        if not user.is_authenticated:
            return
            
        today = datetime.now()
        report_day = getattr(user.settings, 'monthly_report_day', 5) # Default 5th
        
        # If today is before the user's preferred report day, do nothing.
        if today.day < report_day:
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
            
            # Check Notification Methods
            try:
                methods = json.loads(user.settings.notification_methods or '["email"]')
            except:
                methods = ['email']

            # --- Salary Report ---
            try:
                salary_service = SalaryService()
                records = salary_service.get_records_by_range(start_date, end_date, user=user)
                if records:
                    records.sort(key=lambda x: x['date'], reverse=True)
                    total_salary = sum(r.get('amount', 0) for r in records)
                    
                    # 1. Send Email
                    if 'email' in methods:
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
                    
                    # 2. Send LINE
                    if 'line' in methods and user.settings.line_user_id:
                        msg = (
                            f"💰 [薪資報表] {start_date} ~ {end_date}\n"
                            f"總金額: ${total_salary:,}\n"
                            f"筆數: {len(records)} 筆\n"
                            f"------------------\n"
                        )
                        
                        # Add details (All records)
                        detail_lines = []
                        for r in records:
                            # Translate type
                            rtype = "排班" if r['type'] == 'shift' else "獎金"
                            if r['type'] != 'shift' and r['type'] != 'bonus':
                                 rtype = r['type'] # Fallback
                                 
                            line = f"{r['date'][5:]} {rtype} ${r['amount']}"
                            if r['type'] == 'shift':
                                line += f" ({r['hours']}h)"
                            detail_lines.append(line)
                            
                        msg += "\n".join(detail_lines)
                        
                        LineService.push_message(user.settings.line_user_id, msg)

                    # Log it
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
                     
                     # 1. Send Email
                     if 'email' in methods:
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
                     
                     # 2. Send LINE
                     if 'line' in methods and user.settings.line_user_id:
                        msg = (
                            f"💸 [記帳報表] {start_date} ~ {end_date}\n"
                            f"總支出: ${data.get('total_amount', 0):,}\n"
                            f"------------------\n"
                        )
                        
                        # Add details (All records)
                        detail_lines = []
                        for r in records:
                            cat = r.get('category', '其他').split(' ')[0] # Get emoji or just first part
                            detail_lines.append(f"{r['timestamp'][5:16]} {cat} ${int(r['amount'])}")
                            
                        msg += "\n".join(detail_lines)
                        
                        LineService.push_message(user.settings.line_user_id, msg)

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
