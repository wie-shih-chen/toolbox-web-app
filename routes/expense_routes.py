from flask import Blueprint, render_template, request, jsonify
from datetime import datetime
from services.expense_service import ExpenseService

expense_bp = Blueprint('expense', __name__, url_prefix='/expense')
expense_service = ExpenseService()

@expense_bp.route('/')
def index():
    start, end = expense_service.get_current_period()
    return render_template('expense/dashboard.html', start_date=start, end_date=end)

@expense_bp.route('/history')
def history():
    return render_template('expense/history.html')

@expense_bp.route('/settings')
def settings():
    settings = expense_service.get_settings()
    return render_template('expense/settings.html', settings=settings)


@expense_bp.route('/api/records', methods=['GET'])
def get_records():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if not start_date or not end_date:
        start_date, end_date = expense_service.get_current_period()
        
    summary = expense_service.get_summary(start_date, end_date)
    return jsonify(summary)

@expense_bp.route('/api/records', methods=['POST'])
def add_record():
    data = request.json
    if not data or 'amount' not in data:
        return jsonify({"error": "Missing data"}), 400
    
    # Default category emoji mapping help
    categories = {
        "飲食": "🍽️ 飲食",
        "衣著": "👕 衣著",
        "居住": "🏠 居住",
        "交通": "🚌 交通",
        "教育": "📖 教育",
        "娛樂": "🎮 娛樂",
        "其他": "📦 其他"
    }
    
    if data.get('category') in categories:
        data['category'] = categories[data['category']]
    
    record = expense_service.add_record(data)
    return jsonify(record), 201

@expense_bp.route('/api/records/<record_id>', methods=['PUT', 'DELETE'])
def handle_record(record_id):
    if request.method == 'DELETE':
        if expense_service.delete_record(record_id):
            return '', 204
        return jsonify({"error": "Not found"}), 404
    
    data = request.json
    record = expense_service.update_record(record_id, data)
    if record:
        return jsonify(record)
    return jsonify({"error": "Not found"}), 404

@expense_bp.route('/api/history/periods')
def get_periods():
    periods = expense_service.get_monthly_periods()
    return jsonify(periods)

@expense_bp.route('/api/settings', methods=['GET', 'POST'])
def handle_settings():
    if request.method == 'POST':
        data = request.json
        settings = expense_service.update_settings(data)
        return jsonify(settings)
    
    settings = expense_service.get_settings()
    return jsonify(settings)

