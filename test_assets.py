from app import app
from models import db, User, SalaryRecord, ExpenseRecord
from services.finance_service import FinanceService
from datetime import datetime
from dateutil.relativedelta import relativedelta
from sqlalchemy import func

def get_total_assets_loop(user):
    settings = user.settings
    initial = settings.initial_assets or 0.0
    
    first_sal = db.session.query(func.min(SalaryRecord.date)).filter_by(user_id=user.id).scalar()
    first_exp = db.session.query(func.min(ExpenseRecord.timestamp)).filter_by(user_id=user.id).scalar()
    
    earliest_date = datetime.now()
    if first_sal:
        try:
            sd = datetime.strptime(first_sal, '%Y-%m-%d')
            if sd < earliest_date: earliest_date = sd
        except: pass
    if first_exp:
        try:
            ed = datetime.strptime(first_exp[:10], '%Y-%m-%d')
            if ed < earliest_date: earliest_date = ed
        except: pass

    # Get current period start
    cycle_type = settings.finance_cycle_type
    today = datetime.now()
    start_day = settings.billing_cycle_start_day or 10
    
    if cycle_type == 'billing':
        if today.day >= start_day:
            current_start = today.replace(day=start_day)
        else:
            current_start = (today - relativedelta(months=1)).replace(day=start_day)
            
        if earliest_date.day >= start_day:
            loop_start = earliest_date.replace(day=start_day)
        else:
            loop_start = (earliest_date - relativedelta(months=1)).replace(day=start_day)
    else:
        current_start = today.replace(day=1)
        loop_start = earliest_date.replace(day=1)

    # ensure time is midnight
    current_start = current_start.replace(hour=0, minute=0, second=0, microsecond=0)
    loop_start = loop_start.replace(hour=0, minute=0, second=0, microsecond=0)
    
    fs = FinanceService()
    
    total_income = 0
    total_expense = 0
    
    curr = loop_start
    months = 0
    while curr <= current_start:
        months += 1
        # get_summary logic
        period_start = curr
        if cycle_type == 'billing':
            period_end = period_start + relativedelta(months=1) - relativedelta(days=1)
        else:
            period_end = period_start + relativedelta(months=1) - relativedelta(days=1)
            
        summary = fs.get_summary(
            period_start.strftime('%Y-%m-%d'),
            period_end.strftime('%Y-%m-%d'),
            user
        )
        total_income += summary.get('total_income', 0)
        total_expense += summary.get('total_expense', 0)
        
        curr += relativedelta(months=1)
        
    return {
        'months': months,
        'loop_start': loop_start.strftime('%Y-%m-%d'),
        'current_start': current_start.strftime('%Y-%m-%d'),
        'total_income': total_income,
        'total_expense': total_expense,
        'net': initial + total_income - total_expense
    }

with app.app_context():
    # Can't test if DB is empty, but we can verify syntax
    print("Syntax ok")
