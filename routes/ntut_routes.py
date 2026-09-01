from flask import Blueprint, render_template, request, jsonify, current_app, Response
from flask_login import login_required, current_user
from models import db, UserCalendar, UserSettings, SalaryRecord, PeriodRecord
from datetime import datetime, date, timedelta
import os, uuid, requests as http_req, secrets, hashlib

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


# ── Built-in Calendar Settings ────────────────────────────────────────────────

def _hex_to_rgba(hex_color: str, alpha: float) -> str:
    """Convert #RRGGBB to rgba(r, g, b, alpha)."""
    h = hex_color.lstrip('#')
    if len(h) == 6:
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f'rgba({r},{g},{b},{alpha})'
    return hex_color  # fallback


_BUILTIN_TYPES = {
    'salary': {
        'name_field':  'builtin_salary_name',
        'color_field': 'builtin_salary_color',
        'default_name':  '🏷 班表',
        'default_color': '#6366f1',
    },
    'period': {
        'name_field':  'builtin_period_name',
        'color_field': 'builtin_period_color',
        'default_name':  '🩸 週期追蹤',
        'default_color': '#ff4d4f',
    },
}


@ntut_bp.route('/internal/<string:type>/settings', methods=['GET'])
@login_required
def get_builtin_settings(type):
    if type not in _BUILTIN_TYPES:
        return jsonify({'error': '不支援的類型'}), 400
    cfg = _BUILTIN_TYPES[type]
    s   = _get_or_create_settings(current_user.id)
    return jsonify({
        'name':  getattr(s, cfg['name_field'],  None) or cfg['default_name'],
        'color': getattr(s, cfg['color_field'], None) or cfg['default_color'],
    })


@ntut_bp.route('/internal/<string:type>/settings', methods=['PUT'])
@login_required
def update_builtin_settings(type):
    if type not in _BUILTIN_TYPES:
        return jsonify({'error': '不支援的類型'}), 400
    cfg  = _BUILTIN_TYPES[type]
    data = request.json or {}
    s    = _get_or_create_settings(current_user.id)

    name  = data.get('name', '').strip()
    color = data.get('color', '').strip()
    if name:
        setattr(s, cfg['name_field'], name[:50])
    if color:
        setattr(s, cfg['color_field'], color[:10])

    db.session.commit()
    return jsonify({
        'name':  getattr(s, cfg['name_field'],  None) or cfg['default_name'],
        'color': getattr(s, cfg['color_field'], None) or cfg['default_color'],
    })


# ── Internal Event Sources (Read-Only) ────────────────────────────────────────

@ntut_bp.route('/internal/salary-events', methods=['GET'])
@login_required
def internal_salary_events():
    """回傳當前使用者的排班記錄，格式符合 FullCalendar。唯讀。"""
    s     = _get_or_create_settings(current_user.id)
    color = (s.builtin_salary_color or '#6366f1') if s else '#6366f1'
    label = (s.builtin_salary_name  or '🏷 班表')  if s else '🏷 班表'

    records = SalaryRecord.query.filter_by(
        user_id=current_user.id, type='shift'
    ).order_by(SalaryRecord.date.asc()).all()

    from models import Company
    companies = {c.id: c.name for c in Company.query.filter_by(user_id=current_user.id).all()}

    events = []
    for r in records:
        company_name = companies.get(r.company_id, '')
        prefix = f"[{company_name}] " if company_name else ""
        title = f'{prefix}{label} {r.start_time}–{r.end_time}'
        if r.hours:
            title += f' ({r.hours:.1f}h)'
        events.append({
            'id': f'salary_{r.id}',
            'title': title,
            'start': f'{r.date}T{r.start_time}:00' if r.start_time else r.date,
            'end':   f'{r.date}T{r.end_time}:00'   if r.end_time   else r.date,
            'backgroundColor': color,
            'borderColor':     color,
            'textColor':       'white',
            'display':         'block',   # 強制月視圖顯示為彩色方塊（有時間的事件預設為點）
            'extendedProps': {
                'readonly':     True,
                'source_type':  'salary',
                'source_label': label,
                'company_name': company_name,
                'hours':        r.hours,
                'rate':         r.rate,
                'amount':       r.amount,
                'note':         r.note or '',
                'record_id':    r.id,
            }
        })
    return jsonify(events)


@ntut_bp.route('/internal/period-events', methods=['GET'])
@login_required
def internal_period_events():
    """回傳當前使用者的月經歷史+預測，格式符合 FullCalendar。唯讀。"""
    s     = _get_or_create_settings(current_user.id)
    color = (s.builtin_period_color or '#ff4d4f') if s else '#ff4d4f'
    label = (s.builtin_period_name  or '🩸 週期追蹤') if s else '🩸 週期追蹤'

    from services.period_service import PeriodService
    svc = PeriodService(current_user.id)
    now = datetime.now()
    events = svc.get_calendar_events(now.year, now.month)

    for e in events:
        if 'extendedProps' not in e:
            e['extendedProps'] = {}
        e['extendedProps']['readonly']     = True
        e['extendedProps']['source_type']  = 'period'
        e['extendedProps']['source_label'] = label

        event_type = e.get('extendedProps', {}).get('type', '')

        if event_type == 'history':
            # 歷史經期：直接套用使用者主題色（實心）
            e['backgroundColor'] = color
            e['borderColor']     = color

        elif event_type == 'predicted_period':
            # 預測經期：主顏色 20% 定調底色 + 實線邊框，外觀與歷史經期區別
            e['backgroundColor'] = _hex_to_rgba(color, 0.2)
            e['borderColor']     = color
            e['textColor']       = color
            e.pop('className', None)  # 移除虛線樣式（現在有顏色了）

        # fertile_window、ovulation：保留原本語意顏色，不覆蓋

    return jsonify(events)


# ── iCal Export ───────────────────────────────────────────────────────────────

def _generate_ics_token(user_id: int) -> str:
    """Generate a deterministic per-user token for iCal URL."""
    secret = current_app.config.get('SECRET_KEY', 'fallback-secret')
    raw    = f'ics-export:{user_id}:{secret}'
    return hashlib.sha256(raw.encode()).hexdigest()[:40]


@ntut_bp.route('/export/ics-token', methods=['GET'])
@login_required
def get_ics_token():
    """回傳當前使用者的 iCal 訂閱 token 與範例連結。"""
    token = _generate_ics_token(current_user.id)
    base  = request.host_url.rstrip('/')
    return jsonify({
        'token': token,
        'base_url': base,
        'example_url': f'{base}/ntut/export/ics?token={token}&include=salary,period'
    })


@ntut_bp.route('/export/ics', methods=['GET'])
def export_ics():
    """產生並回傳 iCal 格式的日曆檔案。使用 token 驗證，不需登入。"""
    token   = request.args.get('token', '')
    include = request.args.get('include', 'salary,period')  # comma-separated
    include_set = {x.strip() for x in include.split(',')}

    # --- Token 驗證：找到對應的 user ---
    matched_user_id = None
    from models import User
    for user in User.query.all():
        if _generate_ics_token(user.id) == token:
            matched_user_id = user.id
            break

    if matched_user_id is None:
        return Response('Unauthorized', status=401, mimetype='text/plain')

    # --- 產生 iCal 內容 ---
    try:
        from icalendar import Calendar, Event as ICSEvent, vText, vDatetime, vDate
    except ImportError:
        return Response('需要安裝 icalendar 套件', status=500, mimetype='text/plain')

    cal = Calendar()
    cal.add('prodid', '-//Toolbox Web App//ZH')
    cal.add('version', '2.0')
    cal.add('calscale', 'GREGORIAN')
    cal.add('method', 'PUBLISH')
    cal.add('x-wr-calname', '工具箱日曆')
    cal.add('x-wr-timezone', 'Asia/Taipei')
    cal.add('refresh-interval;value=duration', 'PT6H')

    now_dt = datetime.utcnow()

    # --- 排班 ---
    if 'salary' in include_set:
        from models import Company
        companies = {c.id: c.name for c in Company.query.filter_by(user_id=matched_user_id).all()}
        records = SalaryRecord.query.filter_by(
            user_id=matched_user_id, type='shift'
        ).all()
        for r in records:
            ev = ICSEvent()
            ev.add('uid', f'salary-{r.id}@toolbox')
            company_name = companies.get(r.company_id, '')
            prefix = f"[{company_name}] " if company_name else ""
            title = f'{prefix}🏷 上班'
            if r.hours:
                title += f' ({r.hours:.1f}h)'
            ev.add('summary', title)
            ev.add('dtstamp', now_dt)

            if r.start_time and r.end_time:
                from datetime import datetime as _dt, timezone as _tz
                TW_TZ = _tz(timedelta(hours=8))  # Asia/Taipei = UTC+8
                st = _dt.strptime(f'{r.date} {r.start_time}', '%Y-%m-%d %H:%M').replace(tzinfo=TW_TZ)
                et = _dt.strptime(f'{r.date} {r.end_time}',   '%Y-%m-%d %H:%M').replace(tzinfo=TW_TZ)
                if et <= st:
                    et += timedelta(days=1)
                ev.add('dtstart', st)
                ev.add('dtend',   et)
            else:
                ev.add('dtstart', date.fromisoformat(r.date))
                ev.add('dtend',   date.fromisoformat(r.date) + timedelta(days=1))

            desc_parts = []
            if company_name: desc_parts.append(f'公司：{company_name}')
            if r.hours:   desc_parts.append(f'工時：{r.hours:.1f} 小時')
            if r.rate:    desc_parts.append(f'時薪：${r.rate:.0f}')
            if r.amount:  desc_parts.append(f'薪資：${r.amount:,}')
            if r.note:    desc_parts.append(f'備註：{r.note}')
            if desc_parts:
                ev.add('description', '\n'.join(desc_parts))

            ev.add('categories', ['班表'])
            cal.add_component(ev)

    # --- 月經（歷史 + 預測）---
    if 'period' in include_set:
        from services.period_service import PeriodService
        svc = PeriodService(matched_user_id)
        now = datetime.now()
        period_events = svc.get_calendar_events(now.year, now.month)

        for pe in period_events:
            ev = ICSEvent()
            uid_raw  = pe.get('id', f'period-{pe["title"]}-{pe["start"]}')
            ev.add('uid', f'{uid_raw}@toolbox')
            ev.add('summary', pe['title'])
            ev.add('dtstamp', now_dt)

            start_str = pe['start']
            end_str   = pe.get('end', start_str)
            ev.add('dtstart', date.fromisoformat(start_str[:10]))
            ev.add('dtend',   date.fromisoformat(end_str[:10]))

            ev.add('categories', ['週期追蹤'])
            cal.add_component(ev)

    ics_content = cal.to_ical()
    filename    = f'toolbox_{matched_user_id}.ics'
    return Response(
        ics_content,
        status=200,
        mimetype='text/calendar; charset=utf-8',
        headers={
            'Content-Disposition': f'inline; filename="{filename}"',
            'Cache-Control': 'no-cache, no-store',
        }
    )
