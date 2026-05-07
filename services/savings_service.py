from models import db, SavingsGoal, ExpenseRecord, SalaryRecord, UserSettings
from flask_login import current_user
from datetime import datetime, timedelta
from sqlalchemy import func
import json

class SavingsService:
    def get_goals(self, user=None):
        target_user = user or current_user
        if not target_user:
            return []
        goals = SavingsGoal.query.filter_by(user_id=target_user.id).order_by(SavingsGoal.created_at.desc()).all()
        return [self._goal_to_dict(g) for g in goals]

    def add_goal(self, goal_data):
        if not current_user.is_authenticated:
            return None
        
        new_goal = SavingsGoal(
            user_id=current_user.id,
            title=goal_data.get('title'),
            target_amount=float(goal_data.get('target_amount', 0)),
            target_date=goal_data.get('target_date'),
            icon=goal_data.get('icon', '💰'),
            current_amount=float(goal_data.get('current_amount', 0))
        )
        db.session.add(new_goal)
        db.session.commit()
        return self._goal_to_dict(new_goal)

    def update_goal(self, goal_id, goal_data):
        goal = SavingsGoal.query.filter_by(id=goal_id, user_id=current_user.id).first()
        if not goal:
            return None
        
        if 'title' in goal_data: goal.title = goal_data['title']
        if 'target_amount' in goal_data: goal.target_amount = float(goal_data['target_amount'])
        if 'target_date' in goal_data: goal.target_date = goal_data['target_date']
        if 'icon' in goal_data: goal.icon = goal_data['icon']
        if 'current_amount' in goal_data: goal.current_amount = float(goal_data['current_amount'])
        if 'is_active' in goal_data: goal.is_active = bool(goal_data['is_active'])
        
        db.session.commit()
        return self._goal_to_dict(goal)

    def delete_goal(self, goal_id):
        goal = SavingsGoal.query.filter_by(id=goal_id, user_id=current_user.id).first()
        if goal:
            db.session.delete(goal)
            db.session.commit()
            return True
        return False

    def calculate_monthly_surplus(self, year, month, user=None):
        """Calculates surplus for a specific calendar month."""
        target_user = user or current_user
        if not target_user:
            return 0
        
        start_date = f"{year}-{month:02d}-01"
        if month == 12:
            end_date = f"{year+1}-01-01"
        else:
            end_date = f"{year}-{month+1:02d}-01"
        
        # Total Salary in this month
        total_salary = db.session.query(func.sum(SalaryRecord.amount))\
            .filter(SalaryRecord.user_id == target_user.id)\
            .filter(SalaryRecord.date >= start_date)\
            .filter(SalaryRecord.date < end_date)\
            .scalar() or 0
        
        # Total Expenses in this month
        total_expenses = db.session.query(func.sum(ExpenseRecord.amount))\
            .filter(ExpenseRecord.user_id == target_user.id)\
            .filter(ExpenseRecord.timestamp >= start_date)\
            .filter(ExpenseRecord.timestamp < end_date)\
            .scalar() or 0
        
        return total_salary - total_expenses

    def get_savings_progress(self, goal_id):
        goal = SavingsGoal.query.get(goal_id)
        if not goal:
            return None
        
        # For simplicity, we assume 'current_amount' is what the user manually set as "already saved"
        # Plus we could potentially calculate "cumulative surplus" since the goal was created.
        # But usually, it's clearer to let users manually update their current_amount 
        # or show a "Available Surplus" vs "Goal".
        
        # Let's provide a "projected completion date" based on average surplus of last 3 months.
        now = datetime.now()
        surpluses = []
        for i in range(1, 4):
            d = now - timedelta(days=30*i)
            surpluses.append(self.calculate_monthly_surplus(d.year, d.month, user=goal.user))
        
        avg_surplus = sum(surpluses) / len(surpluses) if surpluses else 0
        
        remaining = goal.target_amount - goal.current_amount
        if avg_surplus > 0:
            months_to_go = remaining / avg_surplus
            projected_date = now + timedelta(days=30 * months_to_go)
            projected_date_str = projected_date.strftime('%Y-%m-%d')
        else:
            projected_date_str = "無法預測 (結餘不足)"
            
        percent = min(100, (goal.current_amount / goal.target_amount * 100)) if goal.target_amount > 0 else 0
        
        return {
            "goal": self._goal_to_dict(goal),
            "percent": round(percent, 1),
            "remaining": remaining,
            "avg_monthly_surplus": round(avg_surplus),
            "projected_completion": projected_date_str
        }

    def _goal_to_dict(self, goal):
        return {
            'id': goal.id,
            'title': goal.title,
            'target_amount': goal.target_amount,
            'current_amount': goal.current_amount,
            'target_date': goal.target_date,
            'icon': goal.icon,
            'is_active': goal.is_active,
            'created_at': goal.created_at.strftime('%Y-%m-%d')
        }
