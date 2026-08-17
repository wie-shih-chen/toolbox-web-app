from models import db, ExpenseRecord, SalaryRecord, UserSettings
from flask_login import current_user
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from sqlalchemy import func
from services.expense_service import ExpenseService
from services.salary_service import SalaryService

class FinanceService:
    def __init__(self):
        self.expense_service = ExpenseService()
        self.salary_service = SalaryService()

    def get_settings(self, user=None):
        target_user = user or current_user
        if not target_user.is_authenticated:
            return {}
        return target_user.settings

    def update_settings(self, data):
        if not current_user.is_authenticated:
            return None
            
        settings = current_user.settings
        if 'initial_assets' in data:
            settings.initial_assets = float(data['initial_assets'])
        if 'target_savings_rate' in data:
            settings.target_savings_rate = float(data['target_savings_rate'])
        if 'finance_cycle_type' in data:
            settings.finance_cycle_type = data['finance_cycle_type']
        if 'fixed_extra_income' in data:
            settings.fixed_extra_income = float(data['fixed_extra_income'])
            
        db.session.commit()
        return {
            'initial_assets': settings.initial_assets,
            'target_savings_rate': settings.target_savings_rate,
            'finance_cycle_type': settings.finance_cycle_type,
            'fixed_extra_income': settings.fixed_extra_income
        }

    def get_current_period(self, user=None):
        target_user = user or current_user
        if not target_user.is_authenticated:
            return None, None
            
        settings = target_user.settings
        cycle_type = settings.finance_cycle_type
        
        today = datetime.now()
        
        if cycle_type == 'billing':
            # Use ExpenseService logic
            start_day = settings.billing_cycle_start_day or 10
            if today.day >= start_day:
                start_date = today.replace(day=start_day)
            else:
                start_date = (today - relativedelta(months=1)).replace(day=start_day)
                
            end_date = start_date + relativedelta(months=1) - timedelta(days=1)
            return start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')
        else:
            # Natural month
            start_date = today.replace(day=1)
            next_month = start_date + relativedelta(months=1)
            end_date = next_month - timedelta(days=1)
            return start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')

    def get_summary(self, start_date, end_date, user=None):
        target_user = user or current_user
        if not target_user.is_authenticated:
            return {}
            
        # 1. Get Income (Salary)
        salary_records = SalaryRecord.query.filter(
            SalaryRecord.user_id == target_user.id,
            SalaryRecord.date >= start_date,
            SalaryRecord.date <= end_date
        ).order_by(SalaryRecord.date.desc()).all()
        
        salary_sum = sum(r.amount for r in salary_records)
        fixed_income = target_user.settings.fixed_extra_income or 0.0
        total_income = salary_sum + fixed_income
        
        income_details = []
        if fixed_income > 0:
            income_details.append({'type': 'fixed', 'date': start_date, 'category': '固定額外收入', 'amount': fixed_income})
        for r in salary_records:
            income_details.append({'type': 'salary', 'date': r.date, 'category': '薪水', 'amount': r.amount})
        
        # 2. Get Expense
        expense_records = ExpenseRecord.query.filter(
            ExpenseRecord.user_id == target_user.id,
            func.substr(ExpenseRecord.timestamp, 1, 10) >= start_date,
            func.substr(ExpenseRecord.timestamp, 1, 10) <= end_date
        ).order_by(ExpenseRecord.timestamp.desc()).all()
        
        total_expense = sum(r.amount for r in expense_records)
        expense_details = []
        for r in expense_records:
            expense_details.append({
                'date': r.timestamp[:10],
                'category': r.category,
                'amount': r.amount,
                'note': r.note
            })
        
        # 3. Calculate
        net_income = total_income - total_expense
        savings_rate = 0.0
        if total_income > 0:
            savings_rate = round(max(0, net_income) / total_income * 100, 1)
            
        return {
            'period_start': start_date,
            'period_end': end_date,
            'total_income': total_income,
            'total_expense': total_expense,
            'net_income': net_income,
            'savings_rate': savings_rate,
            'income_details': income_details,
            'expense_details': expense_details
        }

    def get_trend(self, user=None, months=6):
        """Get trend for the past N periods"""
        target_user = user or current_user
        if not target_user.is_authenticated:
            return []
            
        settings = target_user.settings
        cycle_type = settings.finance_cycle_type
        
        today = datetime.now()
        start_day = settings.billing_cycle_start_day or 10
        
        if cycle_type == 'billing':
            if today.day >= start_day:
                current_start = today.replace(day=start_day)
            else:
                current_start = (today - relativedelta(months=1)).replace(day=start_day)
        else:
            current_start = today.replace(day=1)
            
        trends = []
        for i in range(months-1, -1, -1):
            period_start = current_start - relativedelta(months=i)
            if cycle_type == 'billing':
                period_end = period_start + relativedelta(months=1) - timedelta(days=1)
                label = f"{period_start.strftime('%Y-%m')} 週期"
            else:
                period_end = period_start + relativedelta(months=1) - timedelta(days=1)
                label = period_start.strftime('%Y-%m')
                
            summary = self.get_summary(
                period_start.strftime('%Y-%m-%d'), 
                period_end.strftime('%Y-%m-%d'), 
                target_user
            )
            summary['label'] = label
            trends.append(summary)
            
        return trends
        
    def get_total_assets(self, user=None):
        target_user = user or current_user
        if not target_user.is_authenticated:
            return 0
            
        settings = target_user.settings
        initial = settings.initial_assets or 0.0
        
        # Total Income overall
        total_income = db.session.query(func.sum(SalaryRecord.amount)).filter_by(user_id=target_user.id).scalar() or 0
        
        # Total Expense overall
        total_expense = db.session.query(func.sum(ExpenseRecord.amount)).filter_by(user_id=target_user.id).scalar() or 0
        
        return initial + total_income - total_expense
