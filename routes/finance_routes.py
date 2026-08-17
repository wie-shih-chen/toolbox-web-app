from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from services.finance_service import FinanceService

finance_bp = Blueprint('finance', __name__)
finance_service = FinanceService()

@finance_bp.route('/')
@login_required
def index():
    return render_template('finance/dashboard.html')

@finance_bp.route('/api/summary', methods=['GET'])
@login_required
def get_summary():
    start_date, end_date = finance_service.get_current_period()
    if not start_date or not end_date:
        return jsonify({'error': 'Unauthorized'}), 401
    
    summary = finance_service.get_summary(start_date, end_date)
    return jsonify(summary)

@finance_bp.route('/api/trend', methods=['GET'])
@login_required
def get_trend():
    try:
        months = int(request.args.get('months', 6))
    except ValueError:
        months = 6
        
    trends = finance_service.get_trend(months=months)
    return jsonify(trends)

@finance_bp.route('/api/assets', methods=['GET'])
@login_required
def get_assets():
    assets = finance_service.get_total_assets()
    return jsonify({'total_assets': assets})

@finance_bp.route('/api/settings', methods=['GET', 'POST'])
@login_required
def handle_settings():
    if request.method == 'POST':
        data = request.json
        settings = finance_service.update_settings(data)
        if settings:
            return jsonify(settings)
        return jsonify({'error': 'Update failed'}), 400
        
    settings = finance_service.get_settings()
    if settings:
        return jsonify({
            'initial_assets': settings.initial_assets,
            'target_savings_rate': settings.target_savings_rate,
            'finance_cycle_type': settings.finance_cycle_type,
            'fixed_extra_income': getattr(settings, 'fixed_extra_income', 0.0),
            'enable_monthly_savings': getattr(settings, 'enable_monthly_savings', False),
            'monthly_savings_amount': getattr(settings, 'monthly_savings_amount', 0),
            'asset_tracking_start_date': getattr(settings, 'asset_tracking_start_date', None)
        })
    return jsonify({'error': 'Unauthorized'}), 401
