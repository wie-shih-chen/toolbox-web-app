import os
import sys
import argparse
from datetime import datetime, timedelta

# Add parent directory to path so we can import app modules
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from app import app
from models import User
from services.salary_service import SalaryService
from services.expense_service import ExpenseService
from services.email_service import EmailService

def get_billing_period(target_date=None):
    """
    Calculate the billing period for the report triggering on target_date (default today).
    Logic:
    - Trigger Date: 11th of Month M
    - End Date: 10th of Month M (Yesterday)
    - Start Date: 10th of Month M-1
    """
    if target_date is None:
        target_date = datetime.now()
        
    # If explicitly running on a specific date, assume we want the report that *would* be generated then.
    # But usually this script runs daily.
    
    # We want to catch the cycle ending on the 10th of THIS month.
    # So if today is the 11th, we process the cycle ending yesterday.
    
    # Cycle End: 10th of current month
    cycle_end = datetime(target_date.year, target_date.month, 10).strftime('%Y-%m-%d')
    
    # Cycle Start: 10th of previous month
    # Logic: Go back ~32 days from cycle_end and set day to 10
    end_dt = datetime.strptime(cycle_end, '%Y-%m-%d')
    start_dt_raw = end_dt - timedelta(days=20) # Go back to prev month
    cycle_start = datetime(start_dt_raw.year, start_dt_raw.month, 10).strftime('%Y-%m-%d')
    
    return cycle_start, cycle_end

def send_reports(force=False, specific_date=None):
    """
    Check date and send reports.
    :param force: Ignore date check and force send for the calculated period.
    :param specific_date: 'YYYY-MM-DD' string to simulate running on that date.
    """
    
    today = datetime.now()
    if specific_date:
        today = datetime.strptime(specific_date, '%Y-%m-%d')
        
    print(f"Running report script. Today is {today.strftime('%Y-%m-%d')}")
    
    # Check trigger condition (11th of month)
    if not force and today.day != 11:
        print("Not the 11th of the month. Skipping. (Use --force to override)")
        return

    start_date, end_date = get_billing_period(today)
    print(f"Generating reports for period: {start_date} ~ {end_date}")

    salary_service = SalaryService()
    expense_service = ExpenseService()

    with app.app_context():
        users = User.query.all()
        print(f"Found {len(users)} users.")
        
        for user in users:
            if not user.email:
                print(f"Skipping user {user.username} (no email)")
                continue
                
            print(f"Processing user: {user.username} ({user.email})")
            
            # --- Salary Report ---
            try:
                salary_records = salary_service.get_records_by_range(start_date, end_date, user=user)
                if salary_records:
                    # Sort records
                    salary_records.sort(key=lambda x: x['date'], reverse=True)
                    total_salary = sum(r.get('amount', 0) for r in salary_records)
                    
                    EmailService.send_email(
                        to=user.email,
                        subject=f'每月薪資報表 ({start_date} ~ {end_date}) / 自動發送',
                        template='email/salary_export.html',
                        username=user.username,
                        record_count=len(salary_records),
                        export_date=today.strftime('%Y/%m/%d'),
                        total_amount=f"${total_salary:,}",
                        records=salary_records
                    )
                    print(f"  - Salary report sent ({len(salary_records)} records)")
                else:
                    print("  - No salary records found.")
            except Exception as e:
                print(f"  ! Failed to send salary report: {e}")

            # --- Expense Report ---
            try:
                expense_data = expense_service.get_summary(start_date, end_date, user=user)
                expense_records = expense_data['records']
                
                if expense_records:
                    # Calculate stats
                    category_stats = expense_data['category_split']
                    top_categories = sorted(category_stats.items(), key=lambda x: x[1], reverse=True)[:5]
                    
                    EmailService.send_email(
                        to=user.email,
                        subject=f'每月記帳報表 ({start_date} ~ {end_date}) / 自動發送',
                        template='email/expense_export.html',
                        username=user.username,
                        period=f"{start_date} ~ {end_date}",
                        total_amount=f"${expense_data.get('total_amount', 0):,}",
                        records=expense_records,
                        top_categories=top_categories
                    )
                    print(f"  - Expense report sent ({len(expense_records)} records)")
                else:
                    print("  - No expense records found.")
            except Exception as e:
                print(f"  ! Failed to send expense report: {e}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Send monthly reports.')
    parser.add_argument('--force', action='store_true', help='Force send regardless of date')
    parser.add_argument('--date', help='Simulate running on specific date (YYYY-MM-DD)')
    args = parser.parse_args()
    
    send_reports(force=args.force, specific_date=args.date)
