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
        if 'enable_monthly_savings' in data:
            settings.enable_monthly_savings = bool(data['enable_monthly_savings'])
        if 'monthly_savings_amount' in data:
            settings.monthly_savings_amount = int(data['monthly_savings_amount'])
        if 'asset_tracking_start_date' in data:
            settings.asset_tracking_start_date = data['asset_tracking_start_date'] or None
            
        db.session.commit()
        return {
            'initial_assets': settings.initial_assets,
            'target_savings_rate': settings.target_savings_rate,
            'finance_cycle_type': settings.finance_cycle_type,
            'fixed_extra_income': settings.fixed_extra_income,
            'enable_monthly_savings': settings.enable_monthly_savings,
            'monthly_savings_amount': settings.monthly_savings_amount,
            'asset_tracking_start_date': settings.asset_tracking_start_date
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
            
        salary_start_dt = datetime.strptime(start_date, '%Y-%m-%d') - relativedelta(months=1)
        salary_end_dt = datetime.strptime(end_date, '%Y-%m-%d') - relativedelta(months=1)
        
        salary_start = salary_start_dt.strftime('%Y-%m-%d')
        salary_end = salary_end_dt.strftime('%Y-%m-%d')
        
        # 1. Get Income (Salary) - Offset by 1 month backward
        salary_records = SalaryRecord.query.filter(
            SalaryRecord.user_id == target_user.id,
            SalaryRecord.date >= salary_start,
            SalaryRecord.date <= salary_end
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
        savings_goal = 0
        if target_user.settings.enable_monthly_savings:
            savings_goal = target_user.settings.monthly_savings_amount or 0

        net_income = total_income - total_expense - savings_goal
        
        savings_rate = 0.0
        if total_income > 0:
            savings_rate = round(max(0, total_income - total_expense) / total_income * 100, 1)
            
        return {
            'period_start': start_date,
            'period_end': end_date,
            'total_income': total_income,
            'total_expense': total_expense,
            'net_income': net_income,
            'savings_rate': savings_rate,
            'savings_goal': savings_goal,
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
        
    def get_earliest_record_date(self, user=None):
        target_user = user or current_user
        if not target_user.is_authenticated:
            return datetime.now()
            
        first_salary = db.session.query(func.min(SalaryRecord.date)).filter_by(user_id=target_user.id).scalar()
        first_expense = db.session.query(func.min(ExpenseRecord.timestamp)).filter_by(user_id=target_user.id).scalar()
        
        earliest_date = datetime.now()
        if first_salary:
            try:
                sd = datetime.strptime(first_salary, '%Y-%m-%d')
                if sd < earliest_date: earliest_date = sd
            except: pass
        if first_expense:
            try:
                ed = datetime.strptime(first_expense[:10], '%Y-%m-%d')
                if ed < earliest_date: earliest_date = ed
            except: pass
            
        return earliest_date

    def get_total_assets(self, user=None):
        target_user = user or current_user
        if not target_user.is_authenticated:
            return 0
            
        settings = target_user.settings
        initial = settings.initial_assets or 0.0
        cycle_type = settings.finance_cycle_type
        
        # Find earliest record date
        earliest_date = datetime.now()
        if settings.asset_tracking_start_date:
            try:
                if len(settings.asset_tracking_start_date) == 7:
                    earliest_date = datetime.strptime(settings.asset_tracking_start_date, '%Y-%m')
                else:
                    earliest_date = datetime.strptime(settings.asset_tracking_start_date, '%Y-%m-%d')
            except:
                pass
        else:
            earliest_date = self.get_earliest_record_date(target_user)
            
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

        current_start = current_start.replace(hour=0, minute=0, second=0, microsecond=0)
        loop_start = loop_start.replace(hour=0, minute=0, second=0, microsecond=0)
        
        total_income = 0
        total_expense = 0
        
        curr = loop_start
        # Prevent infinite loop in case of bad data, limit to max 10 years (120 months)
        max_months = 120 
        months_count = 0
        
        while curr <= current_start and months_count < max_months:
            months_count += 1
            period_start = curr
            period_end = period_start + relativedelta(months=1) - timedelta(days=1)
            
            summary = self.get_summary(
                period_start.strftime('%Y-%m-%d'),
                period_end.strftime('%Y-%m-%d'),
                target_user
            )
            
            total_income += summary.get('total_income', 0)
            total_expense += summary.get('total_expense', 0)
            
            curr += relativedelta(months=1)
            
        return initial + total_income - total_expense
