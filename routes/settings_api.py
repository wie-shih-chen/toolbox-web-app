from flask import jsonify, request
from flask_login import login_required, current_user
from models import db, User
import json
import re

def register_settings_api(auth_bp):
    """Register auto-save API routes for settings"""
    
    @auth_bp.route('/api/update_email', methods=['POST'])
    @login_required
    def update_email():
        data = request.json
        email = data.get('email')
        
        if not email:
            return jsonify({'error': '請輸入 Email'}), 400
            
        # Check if taken by another user
        existing = User.query.filter_by(email=email).first()
        if existing and existing.id != current_user.id:
            return jsonify({'error': '此 Email 已被其他帳號使用'}), 400
            
        current_user.email = email
        db.session.commit()
        return jsonify({'success': True})
    
    @auth_bp.route('/api/update_notifications', methods=['POST'])
    @login_required
    def update_notifications():
        data = request.json
        methods = data.get('notification_methods', [])
        report_day = data.get('monthly_report_day', 5)
        
        # Validate report_day
        try:
            report_day = int(report_day)
            if report_day < 1 or report_day > 28:
                report_day = 5
        except:
            report_day = 5
            
        current_user.settings.notification_methods = json.dumps(methods)
        current_user.settings.monthly_report_day = report_day
        db.session.commit()
        
        return jsonify({'success': True})
