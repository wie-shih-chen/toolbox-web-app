"""
旅程規劃器路由模組
- GET  /travel/               → 行程列表頁
- GET  /travel/<int:trip_id>  → 行程內頁（景點清單 + 地圖）
- POST /travel/api/trips               → 新增行程
- PUT  /travel/api/trips/<id>          → 修改行程資訊
- DELETE /travel/api/trips/<id>        → 刪除行程
- GET  /travel/api/trips/<id>/stops   → 取得所有景點
- POST /travel/api/trips/<id>/stops   → 新增景點
- PUT  /travel/api/stops/<id>          → 修改景點
- DELETE /travel/api/stops/<id>        → 刪除景點
- POST /travel/api/stops/<id>/complete → 切換打卡狀態
- GET  /travel/api/trips/<id>/export-kml → 匯出 KML
- POST /travel/api/trips/<id>/import-kml → 匯入 KML
"""
from flask import Blueprint, render_template, request, jsonify, abort
from flask_login import login_required, current_user
from models import db, TripPlan, TripStop
from datetime import datetime
import json

travel_bp = Blueprint('travel', __name__, url_prefix='/travel')


# Jinja2 filter for number formatting
@travel_bp.app_template_filter('format_number')
def format_number(value):
    """Format number with thousands separators."""
    try:
        return f'{int(value):,}'
    except (ValueError, TypeError):
        return str(value)


# ─────────────────────────────── Page Routes ───────────────────────────────

@travel_bp.route('/')
@login_required
def index():
    """行程列表頁"""
    trips = (TripPlan.query
             .filter_by(user_id=current_user.id)
             .order_by(TripPlan.updated_at.desc())
             .all())

    # 為每個行程計算統計資訊
    trip_data = []
    all_stops = []
    for trip in trips:
        stops = TripStop.query.filter_by(trip_id=trip.id).all()
        total_expense = sum(s.estimated_expense or 0 for s in stops)
        days = set(s.day_index for s in stops)
        trip_data.append({
            'trip': trip,
            'stop_count': len(stops),
            'day_count': len(days) if days else 1,
            'total_expense': total_expense,
        })
        for s in stops:
            if s.lat and s.lng:
                all_stops.append({
                    'id': s.id,
                    'name': s.name,
                    'lat': s.lat,
                    'lng': s.lng,
                    'trip_title': trip.title,
                })

    return render_template('travel/index.html',
                           trip_data=trip_data,
                           all_stops_json=json.dumps(all_stops, ensure_ascii=False))


@travel_bp.route('/<int:trip_id>')
@login_required
def detail(trip_id):
    """行程內頁"""
    trip = TripPlan.query.filter_by(id=trip_id, user_id=current_user.id).first_or_404()
    stops = (TripStop.query
             .filter_by(trip_id=trip_id)
             .order_by(TripStop.day_index, TripStop.order_index)
             .all())

    # 按 day_index 分組
    days = {}
    for stop in stops:
        d = stop.day_index
        if d not in days:
            days[d] = []
        days[d].append(stop)

    # 序列化景點資料給前端 JS
    stops_json = json.dumps([_stop_to_dict(s) for s in stops], ensure_ascii=False)

    return render_template('travel/detail.html', trip=trip, days=days, stops_json=stops_json)


# ─────────────────────────────── Trip APIs ─────────────────────────────────

@travel_bp.route('/api/trips', methods=['POST'])
@login_required
def create_trip():
    data = request.get_json() or {}
    title = (data.get('title') or '').strip()
    if not title:
        return jsonify({'error': '行程名稱不能為空'}), 400

    trip = TripPlan(
        user_id=current_user.id,
        title=title,
        description=data.get('description', ''),
        start_date=data.get('start_date'),
        end_date=data.get('end_date'),
    )
    db.session.add(trip)
    db.session.commit()
    return jsonify({'id': trip.id, 'title': trip.title}), 201


@travel_bp.route('/api/trips/<int:trip_id>', methods=['PUT'])
@login_required
def update_trip(trip_id):
    trip = TripPlan.query.filter_by(id=trip_id, user_id=current_user.id).first_or_404()
    data = request.get_json() or {}
    if 'title' in data:
        trip.title = data['title'].strip() or trip.title
    if 'description' in data:
        trip.description = data['description']
    if 'start_date' in data:
        trip.start_date = data['start_date']
    if 'end_date' in data:
        trip.end_date = data['end_date']
    trip.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'ok': True})


@travel_bp.route('/api/trips/<int:trip_id>', methods=['DELETE'])
@login_required
def delete_trip(trip_id):
    trip = TripPlan.query.filter_by(id=trip_id, user_id=current_user.id).first_or_404()
    db.session.delete(trip)
    db.session.commit()
    return jsonify({'ok': True})


# ─────────────────────────────── Stop APIs ─────────────────────────────────

@travel_bp.route('/api/trips/<int:trip_id>/stops', methods=['GET'])
@login_required
def get_stops(trip_id):
    trip = TripPlan.query.filter_by(id=trip_id, user_id=current_user.id).first_or_404()
    stops = (TripStop.query
             .filter_by(trip_id=trip_id)
             .order_by(TripStop.day_index, TripStop.order_index)
             .all())
    return jsonify([_stop_to_dict(s) for s in stops])


@travel_bp.route('/api/trips/<int:trip_id>/stops', methods=['POST'])
@login_required
def add_stop(trip_id):
    trip = TripPlan.query.filter_by(id=trip_id, user_id=current_user.id).first_or_404()
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'error': '景點名稱不能為空'}), 400

    day_index = int(data.get('day_index', 0))

    # 計算當天下一個 order_index
    last = (TripStop.query
            .filter_by(trip_id=trip_id, day_index=day_index)
            .order_by(TripStop.order_index.desc())
            .first())
    next_order = (last.order_index + 1) if last else 0

    stop = TripStop(
        trip_id=trip_id,
        day_index=day_index,
        order_index=next_order,
        name=name,
        address=data.get('address', ''),
        lat=data.get('lat'),
        lng=data.get('lng'),
        note=data.get('note', ''),
        estimated_expense=float(data.get('estimated_expense', 0)),
    )
    db.session.add(stop)
    trip.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify(_stop_to_dict(stop)), 201


@travel_bp.route('/api/stops/<int:stop_id>', methods=['PUT'])
@login_required
def update_stop(stop_id):
    stop = TripStop.query.get_or_404(stop_id)
    # Verify ownership
    if stop.trip.user_id != current_user.id:
        abort(403)
    data = request.get_json() or {}
    for field in ('name', 'address', 'note'):
        if field in data:
            setattr(stop, field, data[field])
    for field in ('lat', 'lng', 'estimated_expense'):
        if field in data and data[field] is not None:
            setattr(stop, field, float(data[field]))
    if 'day_index' in data:
        stop.day_index = int(data['day_index'])
    if 'order_index' in data:
        stop.order_index = int(data['order_index'])
    stop.trip.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify(_stop_to_dict(stop))


@travel_bp.route('/api/stops/<int:stop_id>', methods=['DELETE'])
@login_required
def delete_stop(stop_id):
    stop = TripStop.query.get_or_404(stop_id)
    if stop.trip.user_id != current_user.id:
        abort(403)
    trip = stop.trip
    db.session.delete(stop)
    trip.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'ok': True})


@travel_bp.route('/api/stops/<int:stop_id>/complete', methods=['POST'])
@login_required
def toggle_complete(stop_id):
    stop = TripStop.query.get_or_404(stop_id)
    if stop.trip.user_id != current_user.id:
        abort(403)
    stop.is_completed = not stop.is_completed
    db.session.commit()
    return jsonify({'is_completed': stop.is_completed})


# ─────────────────────────────── KML Export/Import ─────────────────────────

@travel_bp.route('/api/trips/<int:trip_id>/export-kml')
@login_required
def export_kml(trip_id):
    from flask import Response
    trip = TripPlan.query.filter_by(id=trip_id, user_id=current_user.id).first_or_404()
    stops = (TripStop.query
             .filter_by(trip_id=trip_id)
             .order_by(TripStop.day_index, TripStop.order_index)
             .all())

    placemarks = ''
    for stop in stops:
        if stop.lat and stop.lng:
            desc = f'Day {stop.day_index + 1} - {stop.address or ""}'
            if stop.note:
                desc += f'\n備註：{stop.note}'
            placemarks += f'''
    <Placemark>
      <name>{_xml_escape(stop.name)}</name>
      <description>{_xml_escape(desc)}</description>
      <Point><coordinates>{stop.lng},{stop.lat},0</coordinates></Point>
    </Placemark>'''

    kml = f'''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>{_xml_escape(trip.title)}</name>
    <description>{_xml_escape(trip.description or '')}</description>
    {placemarks}
  </Document>
</kml>'''

    filename = f"trip_{trip_id}_{trip.title[:20]}.kml"
    return Response(
        kml,
        mimetype='application/vnd.google-earth.kml+xml',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'}
    )


@travel_bp.route('/api/trips/<int:trip_id>/import-kml', methods=['POST'])
@login_required
def import_kml(trip_id):
    trip = TripPlan.query.filter_by(id=trip_id, user_id=current_user.id).first_or_404()

    if 'file' not in request.files:
        return jsonify({'error': '請上傳 KML 檔案'}), 400

    file = request.files['file']
    try:
        import xml.etree.ElementTree as ET
        content = file.read().decode('utf-8')
        root = ET.fromstring(content)
        ns = {'kml': 'http://www.opengis.net/kml/2.2'}

        added = 0
        # 找最大 day_index 和 order_index
        last_stop = (TripStop.query
                     .filter_by(trip_id=trip_id)
                     .order_by(TripStop.day_index.desc(), TripStop.order_index.desc())
                     .first())
        day_idx = (last_stop.day_index if last_stop else 0)
        order_idx = (last_stop.order_index + 1 if last_stop else 0)

        for pm in root.iter('{http://www.opengis.net/kml/2.2}Placemark'):
            name_el = pm.find('{http://www.opengis.net/kml/2.2}name')
            coord_el = pm.find('.//{http://www.opengis.net/kml/2.2}coordinates')
            if name_el is None or coord_el is None:
                continue

            name = (name_el.text or '').strip()
            coords = (coord_el.text or '').strip().split(',')
            if len(coords) < 2:
                continue

            lng, lat = float(coords[0]), float(coords[1])
            stop = TripStop(
                trip_id=trip_id,
                day_index=day_idx,
                order_index=order_idx,
                name=name,
                lat=lat,
                lng=lng,
            )
            db.session.add(stop)
            order_idx += 1
            added += 1

        trip.updated_at = datetime.utcnow()
        db.session.commit()
        return jsonify({'ok': True, 'added': added})
    except Exception as e:
        return jsonify({'error': f'KML 解析失敗：{str(e)}'}), 400


# ─────────────────────────────── Helpers ───────────────────────────────────

def _stop_to_dict(stop):
    return {
        'id':                stop.id,
        'trip_id':           stop.trip_id,
        'day_index':         stop.day_index,
        'order_index':       stop.order_index,
        'name':              stop.name,
        'address':           stop.address or '',
        'lat':               stop.lat,
        'lng':               stop.lng,
        'note':              stop.note or '',
        'estimated_expense': stop.estimated_expense or 0,
        'is_completed':      stop.is_completed,
    }


def _xml_escape(text):
    return (str(text)
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;'))
