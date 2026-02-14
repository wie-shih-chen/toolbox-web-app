from flask import Blueprint, render_template, request, jsonify, url_for, flash, redirect
from flask_login import login_required, current_user
from services.reminder_service import ReminderService
from models import Reminder
from datetime import datetime

reminder_bp = Blueprint('reminder', __name__)

@reminder_bp.route('/')
@login_required
def index():
    reminders = ReminderService.get_user_reminders(current_user.id)
    return render_template('reminders/index.html', reminders=reminders)

@reminder_bp.route('/add', methods=['POST'])
@login_required
def add_reminder():
    data = request.json
    reminder, error = ReminderService.create_reminder(current_user.id, data)
    if error:
        return jsonify({'success': False, 'error': error}), 400
    return jsonify({'success': True, 'message': '提醒已新增'})

@reminder_bp.route('/<int:id>/edit', methods=['POST'])
@login_required
def edit_reminder(id):
    data = request.json
    reminder, error = ReminderService.update_reminder(id, current_user.id, data)
    if error:
        return jsonify({'success': False, 'error': error}), 400
    return jsonify({'success': True, 'message': '提醒已更新'})

@reminder_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete_reminder(id):
    success = ReminderService.delete_reminder(id, current_user.id)
    if success:
        return jsonify({'success': True, 'message': '提醒已刪除'})
    return jsonify({'success': False, 'error': '刪除失敗'}), 400

@reminder_bp.route('/<int:id>/toggle', methods=['POST'])
@login_required
def toggle_reminder(id):
    is_active = ReminderService.toggle_active(id, current_user.id)
    if is_active is not None:
        return jsonify({'success': True, 'is_active': is_active})
    return jsonify({'success': False, 'error': '找不到提醒'}), 400

@reminder_bp.route('/api/list')
@login_required
def list_reminders():
    """API to get current state of reminders for polling."""
    reminders = ReminderService.get_user_reminders(current_user.id)
    data = []
    for r in reminders:
        data.append({
            'id': r.id,
            'is_active': r.is_active
        })
    return jsonify({'success': True, 'reminders': data})
