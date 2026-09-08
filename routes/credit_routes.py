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


@credit_bp.route('/api/fetch_courses')
@login_required
def fetch_courses():
    """從北科大教務系統即時抓取某班級的課表"""
    year = request.args.get('year', '113')
    sem = request.args.get('sem', '1')
    code = request.args.get('code') # 班級代碼 e.g. 2676 (資工四)
    
    if not code:
        return jsonify({"success": False, "error": "Missing class code"})
        
    url = f"https://aps.ntut.edu.tw/course/tw/Subj.jsp?format=-4&year={year}&sem={sem}&code={code}"
    
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        resp.encoding = 'big5' # 北科大網頁編碼通常是 big5 或 utf-8，需要測試。如果是 utf8 可以改。
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        courses = []
        # 尋找課表中的資料列 (避開標題)
        for tr in soup.find_all('tr'):
            tds = tr.find_all('td')
            if len(tds) >= 12: # 確保是一般的課程列
                # 確認第一欄是課號 (數字)
                course_no = tds[0].text.strip()
                if re.match(r'^\d+$', course_no):
                    # 抓取課程資訊
                    courses.append({
                        "course_no": course_no,
                        "name": tds[1].text.strip(),
                        "stage": tds[2].text.strip(),
                        "credits": tds[3].text.strip(),
                        "hours": tds[4].text.strip(),
                        "required": tds[5].text.strip(), # 必選修
                        "teacher": tds[6].text.strip()
                    })
                    
        return jsonify({"success": True, "courses": courses})
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

