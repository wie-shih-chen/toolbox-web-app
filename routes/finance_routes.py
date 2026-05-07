from flask import Blueprint, jsonify, request, render_template
from flask_login import login_required, current_user
from services.savings_service import SavingsService
from services.finance_service import FinanceService
from services.salary_service import SalaryService
from datetime import datetime

finance_bp = Blueprint('finance', __name__)
savings_service = SavingsService()
finance_service = FinanceService()
salary_service = SalaryService()

@finance_bp.route('/savings')
@login_required
def savings_page():
    return render_template('finance/savings.html')

@finance_bp.route('/api/savings/goals', methods=['GET'])
@login_required
def get_goals():
    goals = savings_service.get_goals()
    return jsonify(goals)

@finance_bp.route('/api/savings/goals', methods=['POST'])
@login_required
def add_goal():
    data = request.get_json()
    goal = savings_service.add_goal(data)
    return jsonify(goal)

@finance_bp.route('/api/savings/goals/<int:goal_id>', methods=['PUT'])
@login_required
def update_goal(goal_id):
    data = request.get_json()
    goal = savings_service.update_goal(goal_id, data)
    if goal:
        return jsonify(goal)
    return jsonify({"error": "Goal not found"}), 404

@finance_bp.route('/api/savings/goals/<int:goal_id>', methods=['DELETE'])
@login_required
def delete_goal(goal_id):
    success = savings_service.delete_goal(goal_id)
    return jsonify({"success": success})

@finance_bp.route('/api/savings/progress/<int:goal_id>')
@login_required
def get_progress(goal_id):
    progress = savings_service.get_savings_progress(goal_id)
    if progress:
        return jsonify(progress)
    return jsonify({"error": "Goal not found"}), 404

@finance_bp.route('/api/finance/overview')
@login_required
def finance_overview():
    # Get current month's gross salary from SalaryService
    now = datetime.now()
    # Find current period using salary service logic
    periods = salary_service.get_monthly_periods()
    current_period = periods[-1] if periods else None
    
    if current_period:
        summary = salary_service.get_history_summary(current_period['start'], current_period['end'])
        gross = summary.get('total_amount', 0)
    else:
        gross = 0
        
    finance_summary = finance_service.get_user_finance_summary(gross)
    
    # Get top active goal
    goals = savings_service.get_goals()
    active_goals = [g for g in goals if g['is_active']]
    top_goal_progress = None
    if active_goals:
        top_goal_progress = savings_service.get_savings_progress(active_goals[0]['id'])
        
    return jsonify({
        "finance_summary": finance_summary,
        "top_goal": top_goal_progress,
        "period": current_period
    })
