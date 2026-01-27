from flask import Blueprint, render_template, request, jsonify, Response
from services.salary_service import SalaryService
from datetime import datetime, timedelta

salary_bp = Blueprint('salary', __name__)
service = SalaryService()

@salary_bp.route('/')
def index():
    # Default to current week
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    date_str = monday.strftime('%Y-%m-%d')
    return render_template('salary/dashboard.html', start_date=date_str)

@salary_bp.route('/monthly')
def monthly():
    return render_template('salary/monthly.html')

@salary_bp.route('/history')
def history():
    return render_template('salary/history.html')

@salary_bp.route('/settings')
def settings():
    current_settings = service.get_settings()
    return render_template('salary/settings.html', settings=current_settings)

# ================= MAX API =================

@salary_bp.route('/api/records', methods=['GET'])
def get_records():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if start_date and end_date:
        records = service.get_records_by_range(start_date, end_date)
    else:
        records = service.get_all_records()
        
    return jsonify(records)

@salary_bp.route('/api/records', methods=['POST'])
def add_record():
    data = request.json
    try:
        new_record = service.add_record(data)
        return jsonify(new_record), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@salary_bp.route('/api/records/<record_id>', methods=['PUT'])
def update_record(record_id):
    data = request.json
    try:
        updated_record = service.update_record(record_id, data)
        if updated_record:
            return jsonify(updated_record)
        return jsonify({'error': 'Record not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@salary_bp.route('/api/records/<record_id>', methods=['DELETE'])
def delete_record(record_id):
    if service.delete_record(record_id):
        return jsonify({'success': True})
    return jsonify({'error': 'Record not found'}), 404

@salary_bp.route('/api/stats', methods=['GET'])
def get_stats():
    start_date = request.args.get('start_date')
    summary = service.calculate_weekly_summary(start_date)
    return jsonify(summary)

@salary_bp.route('/api/settings', methods=['GET', 'POST'])
def handle_settings():
    if request.method == 'POST':
        data = request.json
        updated = service.update_settings(data)
        return jsonify(updated)
    return jsonify(service.get_settings())

@salary_bp.route('/api/actions/copy_week', methods=['POST'])
def copy_week():
    target_date = request.json.get('target_date') # The Monday of current week
    if not target_date:
        return jsonify({'error': 'No target date'}), 400
        
    count = service.copy_week_records(target_date)
    return jsonify({'count': count})

@salary_bp.route('/api/actions/clear_week', methods=['POST'])
def clear_week():
    week_start = request.json.get('week_start')
    if not week_start:
        return jsonify({'error': 'No week start'}), 400
        
    count = service.clear_week_records(week_start)
    return jsonify({'count': count})

@salary_bp.route('/api/export', methods=['GET'])
def export_csv():
    csv_content = service.generate_csv_export()
    
    filename = f"salary_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return Response(
        csv_content,
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename={filename}"}
    )

@salary_bp.route('/api/history/periods', methods=['GET'])
def get_history_periods():
    periods = service.get_monthly_periods()
    return jsonify(periods)

@salary_bp.route('/api/history/data', methods=['GET'])
def get_history_data():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if not start_date or not end_date:
        return jsonify({'error': 'Missing dates'}), 400
        
    data = service.get_history_summary(start_date, end_date)
    return jsonify(data)
