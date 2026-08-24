from app import app
from models import db, User
from services.finance_service import FinanceService

finance_service = FinanceService()

with app.app_context():
    user = User.query.first()
    print("User ID:", user.id)
    # Let's mock what get_total_assets does
    settings = user.settings
    print(f"Cycle type: {settings.finance_cycle_type}, Start Day: {settings.billing_cycle_start_day}")
    earliest = finance_service.get_earliest_record_date(user)
    print("Earliest Date:", earliest)
    
    # Check total assets loop
    initial = settings.initial_assets or 0
    total_income = 0
    total_expense = 0
    
    from datetime import datetime, timedelta
    from dateutil.relativedelta import relativedelta
    
    today = datetime.now()
    start_day = settings.billing_cycle_start_day or 10
    
    if settings.finance_cycle_type == 'billing':
        if today.day >= start_day:
            current_start = today.replace(day=start_day)
        else:
            current_start = (today - relativedelta(months=1)).replace(day=start_day)
            
        if earliest.day >= start_day:
            loop_start = earliest.replace(day=start_day)
        else:
            loop_start = (earliest - relativedelta(months=1)).replace(day=start_day)
    else:
        current_start = today.replace(day=1)
        loop_start = earliest.replace(day=1)

    current_start = current_start.replace(hour=0, minute=0, second=0, microsecond=0)
    loop_start = loop_start.replace(hour=0, minute=0, second=0, microsecond=0)
    
    curr = loop_start
    print("Loop starting from:", loop_start, "to", current_start)
    
    while curr <= current_start:
        period_start = curr
        period_end = period_start + relativedelta(months=1) - timedelta(days=1)
        
        summary = finance_service.get_summary(
            period_start.strftime('%Y-%m-%d'),
            period_end.strftime('%Y-%m-%d'),
            user
        )
        
        inc = summary.get('total_income', 0)
        exp = summary.get('total_expense', 0)
        print(f"Period {period_start.strftime('%Y-%m-%d')} to {period_end.strftime('%Y-%m-%d')}: Income = {inc}, Expense = {exp}, Net = {inc - exp}")
        
        total_income += inc
        total_expense += exp
        
        curr += relativedelta(months=1)
        
    print(f"Total calculated: {total_income - total_expense}")
