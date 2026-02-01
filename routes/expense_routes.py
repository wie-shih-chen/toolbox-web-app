from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from datetime import datetime

from services.expense_service import ExpenseService

expense_bp = Blueprint('expense', __name__, url_prefix='/expense')
expense_service = ExpenseService()

@expense_bp.route('/')
@login_required
def index():
    """本週期記帳"""
    start, end = expense_service.get_current_period()
    return render_template('expense/dashboard.html', start_date=start, end_date=end)

@expense_bp.route('/today')
@login_required
def today():
    """本日記帳"""
    return render_template('expense/today.html')


@expense_bp.route('/history')
@login_required
def history():
    return render_template('expense/history.html')

@expense_bp.route('/settings')
@login_required
def settings():
    settings = expense_service.get_settings()
    return render_template('expense/settings.html', settings=settings)


@expense_bp.route('/api/records/grouped', methods=['GET'])
@login_required
def get_grouped_records():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if not start_date or not end_date:
        start_date, end_date = expense_service.get_current_period()
        
    summary = expense_service.get_grouped_summary(start_date, end_date)
    return jsonify(summary)

@expense_bp.route('/api/records', methods=['GET'])
@login_required
def get_records():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if not start_date or not end_date:
        start_date, end_date = expense_service.get_current_period()
        
    summary = expense_service.get_summary(start_date, end_date)
    return jsonify(summary)

@expense_bp.route('/api/records', methods=['POST'])
@login_required
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
@login_required
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
@login_required
def get_periods():
    periods = expense_service.get_monthly_periods()
    return jsonify(periods)

@expense_bp.route('/api/settings', methods=['GET', 'POST'])
@login_required
def handle_settings():
    if request.method == 'POST':
        data = request.json
        settings = expense_service.update_settings(data)
        return jsonify(settings)
    
    settings = expense_service.get_settings()
    return jsonify(settings)
@expense_bp.route('/api/records/export', methods=['GET'])
@login_required
def export_records():
    from flask_login import current_user
    from services.email_service import EmailService
    from flask import Response
    
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if not start_date or not end_date:
        return jsonify({"error": "Missing dates"}), 400
        
    csv_data = expense_service.export_records_csv(start_date, end_date)
    filename = f"expense_export_{start_date}_{end_date}.csv"
    
    # If user has email, send it there
    if current_user.email:
        # Get full data for email rendering
        summary_data = expense_service.get_summary(start_date, end_date)
        records = expense_service.get_records(start_date, end_date)
        
        # Calculate category stats for the email
        category_stats = {}
        for r in records:
            cat = r.get('category', '其他')
            cat_name = cat.split(' ')[1] if ' ' in cat else cat
            category_stats[cat_name] = category_stats.get(cat_name, 0) + r['amount']
            
        # Simplified top 5 categories
        top_categories = sorted(category_stats.items(), key=lambda x: x[1], reverse=True)[:5]
        
        success = EmailService.send_email(
            to=current_user.email,
            subject=f'記帳明細報表 ({start_date} - {end_date})',
            template='email/expense_export.html',
            username=current_user.username,
            period=f"{start_date} ~ {end_date}",
            total_amount=f"${summary_data.get('total_amount', 0):,}",
            records=records,
            top_categories=top_categories
        )
        
        if success:
             return jsonify({
                "success": True, 
                "message": f"報表內容已寄送至 {current_user.email}",
                "method": "email"
            })
    
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename={filename}"}
    )
    
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename={filename}"}
    )
