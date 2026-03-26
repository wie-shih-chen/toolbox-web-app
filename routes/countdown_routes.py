from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from services.countdown_service import CountdownService

countdown_bp = Blueprint('countdown', __name__, url_prefix='/countdown')

@countdown_bp.before_request
@login_required
def require_login():
    pass

@countdown_bp.route('/')
def index():
    """Render the countdown dashboard."""
    service = CountdownService(current_user.id)
    items = service.get_all()
    return render_template('countdown/index.html', items=items)

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
