from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from flask_login import login_required, current_user
from services.countdown_service import CountdownService

countdown_bp = Blueprint('countdown', __name__, url_prefix='/countdown')

@countdown_bp.before_request
def require_login():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))

@countdown_bp.route('/')
def index():
    """Render the countdown dashboard."""
    service = CountdownService(current_user.id)
    items = service.get_all()
    return render_template('countdown/index.html', items=items)

@countdown_bp.route('/<int:item_id>')
def detail(item_id):
    """Render the milestone detail page for a specific countdown."""
    service = CountdownService(current_user.id)
    event = service.get_event(item_id)
    if not event:
        from flask import abort
        abort(404)
    milestones = service.get_milestones(item_id)
    return render_template('countdown/detail.html', event=event, milestones=milestones)

@countdown_bp.route('/api/events', methods=['GET'])
def get_events():
    service = CountdownService(current_user.id)
    return jsonify(service.get_all())

@countdown_bp.route('/api/events', methods=['POST'])
def add_event():
    service = CountdownService(current_user.id)
    return jsonify(service.add_event(request.json))

@countdown_bp.route('/api/events/<int:item_id>', methods=['PUT'])
def update_event(item_id):
    service = CountdownService(current_user.id)
    return jsonify(service.update_event(item_id, request.json))

@countdown_bp.route('/api/events/<int:item_id>', methods=['DELETE'])
def delete_event(item_id):
    service = CountdownService(current_user.id)
    return jsonify(service.delete_event(item_id))

@countdown_bp.route('/api/events/<int:item_id>/toggle-pin', methods=['POST'])
def toggle_pin(item_id):
    service = CountdownService(current_user.id)
    return jsonify(service.toggle_pin(item_id))

@countdown_bp.route('/api/events/<int:item_id>/toggle-notify', methods=['POST'])
def toggle_notify(item_id):
    service = CountdownService(current_user.id)
    from models import Countdown
    item = Countdown.query.filter_by(id=item_id, user_id=current_user.id).first_or_404()
    item.notify_enabled = not item.notify_enabled
    from app import db
    db.session.commit()
    return jsonify({"success": True, "notify_enabled": item.notify_enabled})

# --- Sub-event (Milestone) API ---

@countdown_bp.route('/api/events/<int:item_id>/sub-events', methods=['POST'])
def add_sub_event(item_id):
    service = CountdownService(current_user.id)
    return jsonify(service.add_sub_event(item_id, request.json))

@countdown_bp.route('/api/events/<int:item_id>/sub-events/<int:sub_id>', methods=['PUT'])
def update_sub_event(item_id, sub_id):
    service = CountdownService(current_user.id)
    return jsonify(service.update_sub_event(item_id, sub_id, request.json))

@countdown_bp.route('/api/events/<int:item_id>/sub-events/<int:sub_id>', methods=['DELETE'])
def delete_sub_event(item_id, sub_id):
    service = CountdownService(current_user.id)
    return jsonify(service.delete_sub_event(item_id, sub_id))

