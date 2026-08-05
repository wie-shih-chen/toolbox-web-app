from flask import Blueprint, render_template, request, jsonify, flash
from flask_login import login_required, current_user
from services.period_service import PeriodService

period_bp = Blueprint('period', __name__, url_prefix='/period')

@period_bp.before_request
@login_required
def require_login():
    pass

@period_bp.route('/')
def dashboard():
    """Render the main menstrual tracker dashboard with calendar."""
    service = PeriodService(current_user.id)
    settings = service.settings
    predictions = service.get_predictions(months=1)
    next_prediction = predictions[0] if predictions else None
    history = service.get_history()
    status = service.get_status()
    return render_template(
        'period/dashboard.html',
        settings=settings,
        next_prediction=next_prediction,
        history=history,
        status=status
    )

@period_bp.route('/api/events', methods=['GET'])
def get_events():
    """Returns calendar events suitable for FullCalendar."""
    service = PeriodService(current_user.id)
    year = request.args.get('year')
    month = request.args.get('month')
    
    events = service.get_calendar_events(year, month)
    return jsonify(events)

@period_bp.route('/api/records', methods=['POST'])
def add_record():
    """Add a new period record."""
    data = request.json
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    note = data.get('note')
    exclude_from_avg = data.get('exclude_from_avg', False)
    
    if not start_date:
        return jsonify({"success": False, "error": "Missing start_date"}), 400
        
    service = PeriodService(current_user.id)
    result = service.add_record(start_date, end_date, note, exclude_from_avg)
    return jsonify(result)

@period_bp.route('/api/records/<int:record_id>', methods=['PUT'])
def update_record(record_id):
    """Update an existing period record."""
    data = request.json
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    note = data.get('note')
    exclude_from_avg = data.get('exclude_from_avg')
    
    if not start_date:
        return jsonify({"success": False, "error": "Missing start_date"}), 400
        
    service = PeriodService(current_user.id)
    result = service.update_record(record_id, start_date, end_date, note, exclude_from_avg)
    return jsonify(result)

@period_bp.route('/api/records/<int:record_id>', methods=['DELETE'])
def delete_record(record_id):
    """Delete a period record."""
    service = PeriodService(current_user.id)
    result = service.delete_record(record_id)
    return jsonify(result)

@period_bp.route('/api/quick-start', methods=['POST'])
def quick_start():
    """One-tap: record today as period start."""
    service = PeriodService(current_user.id)
    result = service.quick_start_today()
    return jsonify(result)

@period_bp.route('/api/quick-end', methods=['POST'])
def quick_end():
    """One-tap: set today as end date of the latest open period."""
    service = PeriodService(current_user.id)
    result = service.quick_end_today()
    return jsonify(result)

@period_bp.route('/api/status', methods=['GET'])
def get_status():
    """Return current period status."""
    service = PeriodService(current_user.id)
    return jsonify(service.get_status())

@period_bp.route('/settings', methods=['GET', 'POST'])
def period_settings():
    """Settings page to configure average cycle and duration."""
    service = PeriodService(current_user.id)
    
    if request.method == 'POST':
        avg_cycle = request.form.get('avg_period_cycle')
        avg_duration = request.form.get('avg_period_duration')
        # Checkbox is either 'on' or not present
        notify_enabled = request.form.get('period_notify_enabled') == 'on'
        notify_time = request.form.get('period_notify_time')
        notify_days = request.form.get('period_notify_days_before')
        notify_period = request.form.get('period_notify_period') == 'on'
        notify_ovulation = request.form.get('period_notify_ovulation') == 'on'
        
        stress_level = request.form.get('stress_level')
        sleep_quality = request.form.get('sleep_quality')
        anxiety_multiplier = request.form.get('anxiety_multiplier')
        
        service.update_settings(
            avg_period_cycle=avg_cycle,
            avg_period_duration=avg_duration,
            period_notify_enabled=notify_enabled,
            period_notify_time=notify_time,
            period_notify_days_before=notify_days,
            period_notify_period=notify_period,
            period_notify_ovulation=notify_ovulation,
            stress_level=stress_level,
            sleep_quality=sleep_quality,
            anxiety_multiplier=anxiety_multiplier
        )
        flash('設定已儲存！', 'success')
            
    return render_template('period/settings.html', settings=service.settings)
