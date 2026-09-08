from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from models import db, CreditSetting, CreditCourse
import requests
from bs4 import BeautifulSoup
import re

credit_bp = Blueprint('credit', __name__, url_prefix='/credit')

def get_progress(setting):
    courses = CreditCourse.query.filter_by(setting_id=setting.id).all()
    progress = {'total': 0, 'major_req': 0, 'major_elec': 0, 'common': 0, 'free': 0}
    for c in courses:
        if c.grade not in ['F', 'fail'] and c.category != 'pe':
            progress['total'] += c.credits
            if c.category == 'major_required':
                progress['major_req'] += c.credits
            elif c.category == 'major_elective':
                progress['major_elec'] += c.credits
            elif c.category == 'common_required':
                progress['common'] += c.credits
            elif c.category == 'free_elective':
                progress['free'] += c.credits
                
    def calc_percent(current, required):
        if not required or required == 0:
            return 100 if current > 0 else 0
        p = (current / required) * 100
        return min(p, 100)
        
    percentages = {
        'total': calc_percent(progress['total'], setting.total_required),
        'major_req': calc_percent(progress['major_req'], setting.major_required_credits),
        'major_elec': calc_percent(progress['major_elec'], setting.major_elective_credits),
        'common': calc_percent(progress['common'], setting.common_required),
        'free': calc_percent(progress['free'], setting.free_elective_credits)
    }
    return progress, percentages

@credit_bp.route('/')
@login_required
def index():
    """學分計算儀表板"""
    setting = CreditSetting.query.filter_by(user_id=current_user.id).first()
    if not setting:
        return render_template('credit/settings.html', is_new=True)
    
    courses = CreditCourse.query.filter_by(setting_id=setting.id).all()
    progress, percentages = get_progress(setting)
    
    return render_template('credit/dashboard.html', 
                           setting=setting, 
                           courses=courses,
                           progress=progress,
                           percentages=percentages)


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
        setting.total_required = int(request.form.get('total_required', 128))
        setting.common_required = int(request.form.get('common_required', 28))
        setting.major_required_credits = int(request.form.get('major_required_credits', 58))
        setting.major_elective_credits = int(request.form.get('major_elective_credits', 26))
        setting.free_elective_credits = int(request.form.get('free_elective_credits', 16))
        
        db.session.commit()
        return jsonify({"success": True})
        
    return render_template('credit/settings.html', setting=setting)


@credit_bp.route('/api/add_course', methods=['POST'])
@login_required
def add_course():
    setting = CreditSetting.query.filter_by(user_id=current_user.id).first()
    if not setting:
        return jsonify({"success": False, "error": "尚未設定畢業門檻"})
        
    data = request.json
    
    # 檢查是否已存在 (以課號和學期為準)
    existing = CreditCourse.query.filter_by(
        setting_id=setting.id, 
        course_no=data.get('course_no', '')
    ).first()
    
    if existing and data.get('course_no'):
        return jsonify({"success": False, "error": "此課程已經在清單中"})
        
    course = CreditCourse(
        setting_id=setting.id,
        user_id=current_user.id,
        semester=data.get('semester', ''),
        course_no=data.get('course_no', ''),
        name=data.get('name', ''),
        credits=float(data.get('credits', 0)),
        grade=data.get('grade', 'ongoing')
    )
    
    # 自動判斷分類
    category = 'major_elective'
    ctype = data.get('courseType', '')
    name = data.get('name', '')
    if ctype == '▲':
        category = 'major_required'
    elif '體育' in name:
        category = 'pe'
    elif ctype == '★':
        category = 'major_elective'
    elif ctype == '△':
        category = 'free_elective'
        
    course.category = category
    db.session.add(course)
    db.session.commit()
    
    progress, percentages = get_progress(setting)
    return jsonify({"success": True, "id": course.id, "progress": progress, "percentages": percentages})

@credit_bp.route('/api/delete_course/<int:course_id>', methods=['POST'])
@login_required
def delete_course(course_id):
    course = CreditCourse.query.get_or_404(course_id)
    if course.user_id != current_user.id:
        return jsonify({"success": False, "error": "無權限"}), 403
        
    setting = CreditSetting.query.filter_by(id=course.setting_id).first()
    db.session.delete(course)
    db.session.commit()
    
    progress, percentages = get_progress(setting)
    return jsonify({"success": True, "progress": progress, "percentages": percentages})

@credit_bp.route('/api/edit_course/<int:course_id>', methods=['POST'])
@login_required
def edit_course(course_id):
    course = CreditCourse.query.get_or_404(course_id)
    if course.user_id != current_user.id:
        return jsonify({"success": False, "error": "無權限"}), 403
        
    data = request.json
    if 'credits' in data:
        course.credits = float(data['credits'])
    if 'category' in data:
        course.category = data['category']
    if 'grade' in data:
        course.grade = data['grade']
        course.passed = True if data['grade'] not in ['F', 'fail', 'ongoing'] else (False if data['grade'] in ['F', 'fail'] else None)
        
    setting = CreditSetting.query.filter_by(id=course.setting_id).first()
    db.session.commit()
    
    progress, percentages = get_progress(setting)
    return jsonify({"success": True, "progress": progress, "percentages": percentages})
