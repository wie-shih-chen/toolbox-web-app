from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from models import db, UserCalendar, UserSettings
from datetime import datetime, date
import os, uuid, requests as http_req

ntut_bp = Blueprint('ntut', __name__, url_prefix='/ntut')

# ── helpers ──────────────────────────────────────────────────────────────────

def _get_upload_dir():
    """Return (and create if needed) the per-user ICS upload directory."""
    path = os.path.join(current_app.root_path, 'static', 'uploads',
                        'calendars', str(current_user.id))
    os.makedirs(path, exist_ok=True)
    return path


def _get_or_create_settings(user_id):
    """Return UserSettings for user, creating a row if it doesn't exist yet."""
    s = UserSettings.query.filter_by(user_id=user_id).first()
    if not s:
        s = UserSettings(user_id=user_id)
        db.session.add(s)
        db.session.commit()
    return s


def _parse_ics(content: bytes, color: str = '#4285F4') -> list:
    """Parse ICS bytes → FullCalendar-compatible event dicts."""
    try:
        from icalendar import Calendar
    except ImportError:
        return [{'title': '需要安裝 icalendar 套件', 'start': date.today().isoformat(), 'color': '#f87171'}]

    events = []
    try:
        cal = Calendar.from_ical(content)
        for component in cal.walk():
            if component.name != 'VEVENT':
                continue
            dtstart = component.get('DTSTART')
            dtend   = component.get('DTEND')
            summary = str(component.get('SUMMARY', '（無標題）'))
            if not dtstart:
                continue
            start = dtstart.dt
            end   = dtend.dt if dtend else start

            # icalendar returns date or datetime; convert to ISO 8601
            start_str = start.isoformat()
            end_str   = end.isoformat()

            events.append({
                'title': summary,
                'start': start_str,
                'end':   end_str,
                'color': color,
            })
    except Exception as e:
        print(f'[calendar] ICS parse error: {e}')
    return events


# ── pages ─────────────────────────────────────────────────────────────────────

@ntut_bp.route('/calendar')
@login_required
def calendar():
    return render_template('ntut/calendar.html')


@ntut_bp.route('/calendar/settings')
@login_required
def calendar_settings():
    return render_template('ntut/settings.html')


# ── Settings API ──────────────────────────────────────────────────────────────

@ntut_bp.route('/calendar/settings/api', methods=['GET'])
@login_required
def get_calendar_settings():
    s = _get_or_create_settings(current_user.id)
    import json as _json
    try:
        methods = _json.loads(s.notification_methods or '["email"]')
    except Exception:
        methods = ['email']
    return jsonify({
        'calendar_notify_enabled': s.calendar_notify_enabled,
        'calendar_notify_time':    s.calendar_notify_time or '20:00',
        'notification_methods':    methods,
    })


@ntut_bp.route('/calendar/settings/api', methods=['POST'])
@login_required
def save_calendar_settings():
    data = request.json or {}
    s = _get_or_create_settings(current_user.id)

    if 'calendar_notify_enabled' in data:
        s.calendar_notify_enabled = bool(data['calendar_notify_enabled'])

    if 'calendar_notify_time' in data:
        t = str(data['calendar_notify_time']).strip()
        # Basic HH:MM validation
        parts = t.split(':')
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            s.calendar_notify_time = t

    db.session.commit()
    return jsonify({'success': True})


# ── Calendar CRUD API ─────────────────────────────────────────────────────────

@ntut_bp.route('/calendars', methods=['GET'])
@login_required
def list_calendars():
    cals = UserCalendar.query.filter_by(user_id=current_user.id)\
                             .order_by(UserCalendar.created_at).all()
    return jsonify([{
        'id':             c.id,
        'name':           c.name,
        'source_type':    c.source_type,
        'color':          c.color,
        'notify_enabled': c.notify_enabled,
    } for c in cals])


@ntut_bp.route('/calendars', methods=['POST'])
@login_required
def add_calendar():
    # Detect content type: JSON (url) vs multipart (file)
    if request.content_type and 'application/json' in request.content_type:
        data   = request.json or {}
        name   = data.get('name', '未命名日曆').strip() or '未命名日曆'
        color  = data.get('color', '#4285F4')
        url    = data.get('url', '').strip()
        if not url:
            return jsonify({'error': '請輸入 ICS URL'}), 400
        # Quick validation: try fetching
        try:
            resp = http_req.get(url, timeout=10)
            if resp.status_code != 200:
                return jsonify({'error': f'無法取得 URL（HTTP {resp.status_code}）'}), 400
        except Exception as e:
            return jsonify({'error': f'網路錯誤：{e}'}), 400

        cal = UserCalendar(user_id=current_user.id, name=name,
                           source_type='url', source=url, color=color)
    else:
        # multipart / file upload
        name  = request.form.get('name', '未命名日曆').strip() or '未命名日曆'
        color = request.form.get('color', '#4285F4')
        f     = request.files.get('file')
        if not f:
            return jsonify({'error': '請選擇 .ics 檔案'}), 400
        upload_dir = _get_upload_dir()
        filename   = f'{uuid.uuid4().hex}.ics'
        filepath   = os.path.join(upload_dir, filename)
        f.save(filepath)
        cal = UserCalendar(user_id=current_user.id, name=name,
                           source_type='file', source=filepath, color=color)

    db.session.add(cal)
    db.session.commit()
    return jsonify({
        'id': cal.id, 'name': cal.name,
        'source_type': cal.source_type, 'color': cal.color,
        'notify_enabled': cal.notify_enabled,
    })


@ntut_bp.route('/calendars/<int:cal_id>', methods=['DELETE'])
@login_required
def delete_calendar(cal_id):
    cal = UserCalendar.query.filter_by(id=cal_id, user_id=current_user.id).first()
    if not cal:
        return jsonify({'error': '找不到日曆'}), 404
    if cal.source_type == 'file' and os.path.exists(cal.source):
        os.remove(cal.source)
    db.session.delete(cal)
    db.session.commit()
    return jsonify({'success': True})


@ntut_bp.route('/calendars/<int:cal_id>', methods=['PUT'])
@login_required
def update_calendar(cal_id):
    cal = UserCalendar.query.filter_by(id=cal_id, user_id=current_user.id).first()
    if not cal:
        return jsonify({'error': '找不到日曆'}), 404

    data = request.json or {}
    name = data.get('name', '').strip()
    color = data.get('color', '').strip()

    if name:
        cal.name = name
    if color:
        cal.color = color
    if 'notify_enabled' in data:
        cal.notify_enabled = bool(data['notify_enabled'])

    db.session.commit()
    return jsonify({
        'id': cal.id,
        'name': cal.name,
        'color': cal.color,
        'source_type': cal.source_type,
        'notify_enabled': cal.notify_enabled,
    })


@ntut_bp.route('/calendars/<int:cal_id>/events', methods=['GET'])
@login_required
def get_events(cal_id):
    cal = UserCalendar.query.filter_by(id=cal_id, user_id=current_user.id).first()
    if not cal:
        return jsonify([])
    try:
        if cal.source_type == 'url':
            resp    = http_req.get(cal.source, timeout=15)
            content = resp.content
        else:
            with open(cal.source, 'rb') as f:
                content = f.read()
        return jsonify(_parse_ics(content, cal.color))
    except Exception as e:
        return jsonify({'error': str(e)}), 500
