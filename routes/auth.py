from flask import Blueprint, render_template, redirect, url_for, flash, request, session, jsonify, send_file, current_app
from werkzeug.utils import secure_filename
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User, SalaryRecord, ExpenseRecord, UserSettings
from services.email_service import EmailService
from datetime import datetime
import json
import os
import re
from config import Config

from routes.settings_api import register_settings_api

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# Register auto-save API routes
register_settings_api(auth_bp)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if not username or not password or not email:
            flash('請填寫所有欄位')
            return render_template('auth/register.html')
            
        # Validation
        if not re.match("^[a-zA-Z0-9]+$", username):
            flash('使用者名稱只能包含英文字母和數字')
            return render_template('auth/register.html')
            
        if not re.match("^[a-zA-Z0-9]+$", password):
            flash('密碼只能包含英文字母和數字')
            return render_template('auth/register.html')
            
        if password != confirm_password:
            flash('兩次密碼輸入不一致')
            return render_template('auth/register.html')
        
        # Check Existing
        if User.query.filter_by(username=username).first():
            flash('使用者名稱已被使用')
            return render_template('auth/register.html')
            
        if User.query.filter_by(email=email).first():
            flash('此 Email 已被註冊')
            return render_template('auth/register.html')
        
        # Create new user
        new_user = User(username=username, email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        
        # Initialize Settings
        settings = UserSettings(user_id=new_user.id)
        db.session.add(settings)
        db.session.commit()
        
        # Send Welcome Email
        EmailService.send_welcome_email(new_user)
        
        # Legacy Migration
        if User.query.count() == 1:
            migrate_legacy_data(new_user)
            flash('註冊成功！舊有資料已遷移至您的帳號。')
        else:
            flash('註冊成功！請登入。')
            
        return redirect(url_for('auth.login'))
        
    return render_template('auth/register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user, remember=True)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.index'))
        
        flash('帳號或密碼錯誤')
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        
        if user:
            token = user.get_reset_token()
            if EmailService.send_password_reset_email(user, token):
                flash('重設密碼連結已發送至您的信箱，請查看郵件 (30分鐘內有效)')
                return redirect(url_for('auth.login'))
            else:
                flash('發送郵件失敗，請稍後再試')
        else:
            flash('此 Email 尚未註冊')
            
    return render_template('auth/forgot_password.html')

@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    user = User.verify_reset_token(token)
    if not user:
        flash('無效或過期的連結，請重新申請')
        return redirect(url_for('auth.forgot_password'))

    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('兩次密碼輸入不一致')
            return render_template('auth/reset_password.html', token=token) # Pass token for form action

        if not re.match("^[a-zA-Z0-9]+$", password):
            flash('密碼只能包含英文字母和數字')
            return render_template('auth/reset_password.html', token=token)
            
        user.set_password(password)
        db.session.commit()
        
        flash('密碼重設成功，請使用新密碼登入')
        return redirect(url_for('auth.login'))
            
    return render_template('auth/reset_password.html', token=token)

@auth_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    import random
    from datetime import timedelta

    if request.method == 'POST':
        action = request.form.get('action')
        
        # --- Notification Preferences ---
        if action == 'update_notifications':
            methods = request.form.getlist('notification_methods') # returns list of values e.g. ['email', 'line']
            # Store as JSON string
            current_user.settings.notification_methods = json.dumps(methods)
            current_user.settings.notification_methods = json.dumps(methods)
            
            # Update Monthly Report Day
            try:
                day = int(request.form.get('monthly_report_day', 5))
                if 1 <= day <= 28:
                    current_user.settings.monthly_report_day = day
            except ValueError:
                pass
                
            db.session.commit()
            flash('通知設定已更新')
            
        # --- LINE Binding ---
        elif action == 'generate_binding_code':
            # Generate 6-digit code
            code = str(random.randint(100000, 999999))
            current_user.settings.binding_code = code
            current_user.settings.binding_expiry = datetime.now() + timedelta(minutes=5)
            db.session.commit()
            flash(f'驗證碼已產生：{code} (5分鐘內有效)')
            
        elif action == 'unbind_line':
            current_user.settings.line_user_id = None
            db.session.commit()
            flash('已解除 LINE 綁定')

        # --- Profile Updates ---
        else:
            # Update Email
            email = request.form.get('email')
            if email and email != current_user.email:
                if User.query.filter_by(email=email).first():
                    flash('此 Email 已被其他帳號使用')
                else:
                    current_user.email = email
                    db.session.commit()
                    flash('Email 更新成功')
            
            # Update Password
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')
            
            if new_password:
                if new_password != confirm_password:
                    flash('兩次密碼輸入不一致')
                elif not re.match("^[a-zA-Z0-9]+$", new_password):
                    flash('密碼只能包含英文字母和數字')
                else:
                    current_user.set_password(new_password)
                    db.session.commit()
                    flash('密碼更新成功')

    # Prepare view data
    try:
        current_methods = json.loads(current_user.settings.notification_methods or '["email"]')
    except:
        current_methods = ['email']

    return render_template('auth/settings.html', notification_methods=current_methods)

@auth_bp.route('/check_line_status')
@login_required
def check_line_status():
    is_linked = current_user.settings.line_user_id is not None
    return jsonify({'linked': is_linked})

@auth_bp.route('/test_notification', methods=['POST'])
@login_required
def test_notification():
    from services.line_service import LineService
    from services.email_service import EmailService
    
    methods = request.json.get('methods', [])
    results = []
    
    # Test LINE
    if 'line' in methods:
        if not current_user.settings.line_user_id:
            results.append("LINE: 未綁定 ⚠️")
        else:
            try:
                msg = "👋 這是來自工具箱的測試訊息！\n恭喜您，LINE 通知功能設定成功！🎉"
                if LineService.push_message(current_user.settings.line_user_id, msg):
                    results.append("LINE: 發送成功 ✅")
                else:
                    results.append("LINE: 發送失敗 ❌")
            except Exception as e:
                results.append(f"LINE: 錯誤 ({str(e)}) ❌")

    # Test Email
    if 'email' in methods:
        if not current_user.email:
            results.append("Email: 未設定 ⚠️")
        else:
            try:
                if EmailService.send_email(
                    current_user.email,
                    '測試通知 - 工具箱 Web',
                    'email/test_notification.html',
                    user=current_user
                ):
                    results.append("Email: 發送成功 ✅")
                else:
                    results.append("Email: 發送失敗 ❌")
            except Exception as e:
                results.append(f"Email: 錯誤 ({str(e)}) ❌")
    
    if not results:
        return jsonify({'success': False, 'message': '未選擇有效的通知方式'}), 400
        
    return jsonify({
        'success': True, 
        'message': "\\n".join(results)
    })

# ================= DATA MANAGEMENT =================
@auth_bp.route('/data/export_excel', methods=['POST'])
@login_required
def export_excel_all():
    from services.data_service import DataService
    try:
        output = DataService.export_all_data(current_user.id)
        filename = f"toolbox_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        flash(f'匯出失敗: {str(e)}')
        return redirect(url_for('auth.settings'))

@auth_bp.route('/data/reset', methods=['POST'])
@login_required
def reset_data():
    module = request.form.get('module') # 'salary', 'expense'
    confirmation = request.form.get('confirmation')
    
    if confirmation != 'DELETE':
        flash('確認碼錯誤，操作取消')
        return redirect(url_for('auth.settings'))
        
    from services.data_service import DataService
    if DataService.reset_data(current_user.id, module):
        flash('資料重置成功')
    else:
        flash('資料重置失敗')
        
    return redirect(url_for('auth.settings'))

# ================= AVATAR =================
@auth_bp.route('/avatar/preset', methods=['POST'])
@login_required
def set_preset_avatar():
    preset_name = request.json.get('preset')
    if preset_name:
        current_user.avatar_type = 'preset'
        current_user.avatar_val = preset_name
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False}), 400

@auth_bp.route('/avatar/upload', methods=['POST'])
@login_required
def upload_avatar():
    if 'avatar_file' not in request.files:
        flash('未選擇檔案')
        return redirect(url_for('auth.settings'))
        
    file = request.files['avatar_file']
    if file.filename == '':
        flash('未選擇檔案')
        return redirect(url_for('auth.settings'))
        
    if file:
        filename = secure_filename(f"user_{current_user.id}_{int(datetime.now().timestamp())}.png")
        save_path = os.path.join(current_app.root_path, 'static', 'uploads', 'avatars', filename)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        file.save(save_path)
        
        current_user.avatar_type = 'upload'
        current_user.avatar_val = filename
        db.session.commit()
        flash('頭像上傳成功')
        
    return redirect(url_for('auth.settings'))

def migrate_legacy_data(user):
    """Migrate JSON data to SQLite for the given user"""
    try:
        # Migrate Salary Data
        salary_file = Config.SALARY_DATA_FILE
        if os.path.exists(salary_file):
            with open(salary_file, 'r', encoding='utf-8') as f:
                s_data = json.load(f)
                
            # Settings
            if 'settings' in s_data:
                user.settings.hourly_rate = float(s_data['settings'].get('hourly_rate', 183.0))
            
            # Records
            for r in s_data.get('records', []):
                new_record = SalaryRecord(
                    user_id=user.id,
                    date=r['date'],
                    type=r['type'],
                    amount=r['amount'],
                    note=r.get('note')
                )
                if r['type'] == 'shift':
                    new_record.start_time = r.get('start_time')
                    new_record.end_time = r.get('end_time')
                    new_record.hours = float(r.get('hours', 0.0))
                    new_record.rate = float(r.get('rate', 0.0))
                
                db.session.add(new_record)
            
        # Migrate Expense Data
        expense_file = os.path.join(os.path.dirname(Config.SALARY_DATA_FILE), 'expense_data.json')
        if os.path.exists(expense_file):
            with open(expense_file, 'r', encoding='utf-8') as f:
                e_data = json.load(f)
                
            # Settings
            if 'settings' in e_data:
                user.settings.monthly_budget = float(e_data['settings'].get('monthly_budget', 10000.0))
                
            # Records
            for r in e_data.get('records', []):
                new_record = ExpenseRecord(
                    user_id=user.id,
                    timestamp=r.get('timestamp'),
                    category=r.get('category'),
                    note=r.get('note'),
                    amount=float(r.get('amount', 0.0))
                )
                db.session.add(new_record)
                
        db.session.commit()
        print("Migration completed successfully.")
        
    except Exception as e:
        db.session.rollback()
        print(f"Migration failed: {e}")
