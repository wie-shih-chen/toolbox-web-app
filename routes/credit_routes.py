from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from models import db, CreditSetting, CreditCourse
import requests
from bs4 import BeautifulSoup
import re

credit_bp = Blueprint('credit', __name__, url_prefix='/credit')

@credit_bp.route('/')
@login_required
def index():
    """學分計算儀表板"""
    setting = CreditSetting.query.filter_by(user_id=current_user.id).first()
    if not setting:
        return render_template('credit/settings.html', is_new=True)
    
    courses = CreditCourse.query.filter_by(setting_id=setting.id).all()
    # TODO: 計算進度
    
    return render_template('credit/dashboard.html', setting=setting, courses=courses)


@credit_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    """設定畢業門檻與系所資訊"""
    setting = CreditSetting.query.filter_by(user_id=current_user.id).first()
    
    if request.method == 'POST':
        if not setting:
            setting = CreditSetting(user_id=current_user.id)
            db.session.add(setting)
            
        setting.department = request.form.get('department', '')
        setting.entry_year = int(request.form.get('entry_year', 113))
        setting.class_code = request.form.get('class_code', '')
        setting.class_name = request.form.get('class_name', '')
        
        # 門檻設定
        setting.total_required = int(request.form.get('total_required', 132))
        setting.common_required = int(request.form.get('common_required', 28))
        setting.major_required_credits = int(request.form.get('major_required_credits', 64))
        setting.major_elective_credits = int(request.form.get('major_elective_credits', 20))
        setting.free_elective_credits = int(request.form.get('free_elective_credits', 20))
        
        db.session.commit()
        return jsonify({"success": True})
        
    return render_template('credit/settings.html', setting=setting, is_new=False)


@credit_bp.route('/api/add_course', methods=['POST'])
@login_required
def add_course():
    """手動或匯入新增課程"""
    setting = CreditSetting.query.filter_by(user_id=current_user.id).first()
    if not setting:
        return jsonify({"success": False, "error": "請先完成設定"})
        
    data = request.json
    
    # Check if already added
    existing = CreditCourse.query.filter_by(
        setting_id=setting.id, 
        course_no=data.get('course_no', '')
    ).first()
    
    if existing and data.get('course_no'):
        return jsonify({"success": False, "error": "此課程已經在清單中"})

    # Determine category intelligently based on NTUT standard
    course_type = data.get('courseType', '') # △/▲/★
    name = data.get('name', '')
    category = data.get('category', 'major_elective') # Default to major elective
    
    if course_type == '▲':
        category = 'major_required'
    elif '體育' in name:
        category = 'pe'
    elif course_type == '★':
        category = 'major_elective'
    elif course_type == '△':
        category = 'free_elective'

    new_course = CreditCourse(
        setting_id=setting.id,
        user_id=current_user.id,
        course_no=data.get('course_no', ''),
        name=name,
        credits=float(data.get('credits', 3.0)),
        semester=data.get('semester', ''),
        category=category,
        grade='ongoing'
    )
    
    db.session.add(new_course)
    db.session.commit()
    return jsonify({"success": True, "id": new_course.id})

@credit_bp.route('/api/delete_course/<int:course_id>', methods=['POST'])
@login_required
def delete_course(course_id):
    """刪除課程"""
    course = CreditCourse.query.get_or_404(course_id)
    if course.user_id != current_user.id:
        return jsonify({"success": False, "error": "Unauthorized"}), 403
        
    db.session.delete(course)
    db.session.commit()
    return jsonify({"success": True})

@credit_bp.route('/api/edit_course/<int:course_id>', methods=['POST'])
@login_required
def edit_course(course_id):
    """編輯課程"""
    course = CreditCourse.query.get_or_404(course_id)
    if course.user_id != current_user.id:
        return jsonify({"success": False, "error": "Unauthorized"}), 403
        
    data = request.json
    
    if 'credits' in data:
        course.credits = float(data['credits'])
    if 'category' in data:
        course.category = data['category']
    if 'grade' in data:
        course.grade = data['grade']
        course.passed = True if data['grade'] not in ['F', 'fail', 'ongoing'] else (False if data['grade'] in ['F', 'fail'] else None)
        
    db.session.commit()
    return jsonify({"success": True})

