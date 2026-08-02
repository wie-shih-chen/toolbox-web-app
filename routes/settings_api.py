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

    @auth_bp.route('/api/update_custom_categories', methods=['POST'])
    @login_required
    def update_custom_categories():
        try:
            data = request.json
            categories = data.get('categories', [])
            
            print(f"[DEBUG] update_custom_categories - Received: {categories}")
            print(f"[DEBUG] Type check: {type(categories)}")
            
            # Strict Validation: List of Dicts with 'name'
            if not isinstance(categories, list):
                print(f"[ERROR] Invalid type: expected list, got {type(categories)}")
                return jsonify({'error': 'Invalid format: expected array'}), 400
            
            valid_cats = [c for c in categories if isinstance(c, dict) and 'name' in c]
            print(f"[DEBUG] Valid categories after filter: {valid_cats}")
            
            # Save to database
            json_str = json.dumps(valid_cats, ensure_ascii=False)
            print(f"[DEBUG] JSON string to save: {json_str}")
            
            current_user.settings.custom_categories = json_str
            db.session.commit()
            
            # Verify the data was actually saved
            db.session.refresh(current_user.settings)
            saved_data = current_user.settings.custom_categories
            print(f"[VERIFY] Data after commit: {saved_data}")
            
            return jsonify({
                'success': True,
                'saved_count': len(valid_cats),
                'data': valid_cats
            })
            
        except Exception as e:
            print(f"[ERROR] Exception in update_custom_categories: {str(e)}")
            db.session.rollback()
            return jsonify({'error': f'Server error: {str(e)}'}), 500

    @auth_bp.route('/api/update_recurring_expenses', methods=['POST'])
    @login_required
    def update_recurring_expenses():
        try:
            data = request.json
            expenses = data.get('expenses', [])
            
            print(f"[DEBUG] update_recurring_expenses - Received: {expenses}")
            
            if not isinstance(expenses, list):
                print(f"[ERROR] Invalid type: expected list, got {type(expenses)}")
                return jsonify({'error': 'Invalid format: expected array'}), 400
            
            valid_recs = [e for e in expenses if isinstance(e, dict) and 'name' in e]
            print(f"[DEBUG] Valid expenses after filter: {valid_recs}")
            
            json_str = json.dumps(valid_recs, ensure_ascii=False)
            current_user.settings.recurring_expenses = json_str
            db.session.commit()
            
            # Verify
            db.session.refresh(current_user.settings)
            saved_data = current_user.settings.recurring_expenses
            print(f"[VERIFY] Data after commit: {saved_data}")
            
            return jsonify({
                'success': True,
                'saved_count': len(valid_recs),
                'data': valid_recs
            })
            
        except Exception as e:
            print(f"[ERROR] Exception in update_recurring_expenses: {str(e)}")
            db.session.rollback()
            return jsonify({'error': f'Server error: {str(e)}'}), 500

    @auth_bp.route('/api/update_quick_shortcuts', methods=['POST'])
    @login_required
    def update_quick_shortcuts():
        try:
            data = request.json
            shortcuts = data.get('shortcuts', [])
            
            print(f"[DEBUG] update_quick_shortcuts - Received: {shortcuts}")
            
            if not isinstance(shortcuts, list):
                print(f"[ERROR] Invalid type: expected list, got {type(shortcuts)}")
                return jsonify({'error': 'Invalid format: expected array'}), 400
            
            valid_shorts = [s for s in shortcuts if isinstance(s, dict) and 'name' in s]
            print(f"[DEBUG] Valid shortcuts after filter: {valid_shorts}")
            
            json_str = json.dumps(valid_shorts, ensure_ascii=False)
            current_user.settings.quick_shortcuts = json_str
            db.session.commit()
            
            # Verify
            db.session.refresh(current_user.settings)
            saved_data = current_user.settings.quick_shortcuts
            print(f"[VERIFY] Data after commit: {saved_data}")
            
            return jsonify({
                'success': True,
                'saved_count': len(valid_shorts),
                'data': valid_shorts
            })
            
        except Exception as e:
            print(f"[ERROR] Exception in update_quick_shortcuts: {str(e)}")
            db.session.rollback()
            return jsonify({'error': f'Server error: {str(e)}'}), 500

    @auth_bp.route('/api/update_layout', methods=['POST'])
    @login_required
    def update_layout():
        try:
            data = request.json
            dashboard_order = data.get('dashboard_order', [])
            dock_order = data.get('dock_order', [])
            
            if not isinstance(dashboard_order, list) or not isinstance(dock_order, list):
                return jsonify({'error': 'Invalid format: expected array'}), 400
                
            current_user.settings.dashboard_order = json.dumps(dashboard_order, ensure_ascii=False)
            current_user.settings.dock_order = json.dumps(dock_order[:5], ensure_ascii=False) # max 5 items
            db.session.commit()
            
            return jsonify({'success': True})
            
        except Exception as e:
            print(f"[ERROR] Exception in update_layout: {str(e)}")
            db.session.rollback()
            return jsonify({'error': f'Server error: {str(e)}'}), 500
