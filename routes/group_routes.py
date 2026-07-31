import os
import random
import string
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from models import db, User, StudyGroup, GroupMember, GroupDailyRecord, VocabHistoryLog, VocabProgress

group_bp = Blueprint('group', __name__, url_prefix='/group')

def get_tw_today_str():
    tw_now = datetime.utcnow() + timedelta(hours=8)
    return tw_now.strftime('%Y-%m-%d')

def get_tw_today_start_utc():
    tw_now = datetime.utcnow() + timedelta(hours=8)
    tw_midnight = tw_now.replace(hour=0, minute=0, second=0, microsecond=0)
    return tw_midnight - timedelta(hours=8)

def generate_invite_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

@group_bp.route('/')
@login_required
def index():
    # List groups the user is in
    memberships = GroupMember.query.filter_by(user_id=current_user.id).all()
    groups = []
    for m in memberships:
        group = StudyGroup.query.get(m.group_id)
        if group:
            groups.append(group)
    return render_template('vocab/group_list.html', groups=groups)

@group_bp.route('/create', methods=['POST'])
@login_required
def create_group():
    name = request.form.get('name', '').strip()
    daily_goal = request.form.get('daily_goal', type=int)
    
    if not name:
        flash('請輸入群組名稱', 'error')
        return redirect(url_for('group.index'))
    
    if not daily_goal or daily_goal < 10:
        daily_goal = 10
        
    code = generate_invite_code()
    while StudyGroup.query.filter_by(invite_code=code).first():
        code = generate_invite_code()
        
    new_group = StudyGroup(name=name, invite_code=code, owner_id=current_user.id, daily_goal=daily_goal)
    db.session.add(new_group)
    db.session.commit()
    
    # Add creator as member
    member = GroupMember(group_id=new_group.id, user_id=current_user.id)
    db.session.add(member)
    db.session.commit()
    
    flash(f'群組「{name}」建立成功！邀請碼為：{code}', 'success')
    return redirect(url_for('group.index'))

@group_bp.route('/join', methods=['POST'])
@login_required
def join_group():
    code = request.form.get('invite_code', '').strip().upper()
    group = StudyGroup.query.filter_by(invite_code=code).first()
    
    if not group:
        flash('找不到此邀請碼對應的群組', 'error')
        return redirect(url_for('group.index'))
        
    existing = GroupMember.query.filter_by(group_id=group.id, user_id=current_user.id).first()
    if existing:
        flash('您已經在這個群組中了', 'info')
        return redirect(url_for('group.index'))
        
    member = GroupMember(group_id=group.id, user_id=current_user.id)
    db.session.add(member)
    db.session.commit()
    
    flash(f'成功加入群組「{group.name}」！', 'success')
    return redirect(url_for('group.dashboard', group_id=group.id))

@group_bp.route('/<int:group_id>')
@login_required
def dashboard(group_id):
    group = StudyGroup.query.get_or_404(group_id)
    
    # Verify membership
    member = GroupMember.query.filter_by(group_id=group.id, user_id=current_user.id).first()
    if not member:
        flash('您不是這個群組的成員', 'error')
        return redirect(url_for('group.index'))
        
    memberships = GroupMember.query.filter_by(group_id=group.id).all()
    today_str = get_tw_today_str()
    today_start_utc = get_tw_today_start_utc()
    
    dashboard_data = []
    current_user_record = None
    
    for m in memberships:
        user = User.query.get(m.user_id)
        if not user:
            continue
            
        # Get or create today's record
        record = GroupDailyRecord.query.filter_by(group_id=group.id, user_id=user.id, date=today_str).first()
        if not record:
            record = GroupDailyRecord(group_id=group.id, user_id=user.id, date=today_str)
            db.session.add(record)
            db.session.commit()
            
        # Calculate words studied today for this user
        # A word is counted if it has a VocabHistoryLog created >= today_start_utc
        # We need unique words studied today
        logs = VocabHistoryLog.query.filter(
            VocabHistoryLog.user_id == user.id,
            VocabHistoryLog.created_at >= today_start_utc
        ).all()
        unique_words = {log.word for log in logs}
        
        record.words_studied = len(unique_words)
        db.session.commit()
        
        data = {
            'user': user,
            'record': record,
            'is_me': user.id == current_user.id
        }
        dashboard_data.append(data)
        
        if user.id == current_user.id:
            current_user_record = record
            
    # Sort by quiz_score DESC, then words_studied DESC
    dashboard_data.sort(key=lambda x: (x['record'].quiz_score, x['record'].words_studied), reverse=True)
    
    return render_template('vocab/group_dashboard.html', 
                           group=group, 
                           dashboard_data=dashboard_data, 
                           current_user_record=current_user_record,
                           today_str=today_str)

@group_bp.route('/<int:group_id>/quiz')
@login_required
def take_quiz(group_id):
    group = StudyGroup.query.get_or_404(group_id)
    member = GroupMember.query.filter_by(group_id=group.id, user_id=current_user.id).first()
    if not member:
        return redirect(url_for('group.index'))
        
    today_str = get_tw_today_str()
    record = GroupDailyRecord.query.filter_by(group_id=group.id, user_id=current_user.id, date=today_str).first()
    
    if not record or record.words_studied < group.daily_goal:
        flash(f'必須先背滿 {group.daily_goal} 個單字才能開始今日測驗喔！', 'warning')
        return redirect(url_for('group.dashboard', group_id=group.id))
        
    return render_template('vocab/group_quiz.html', group=group, record=record)

@group_bp.route('/<int:group_id>/api/quiz_words')
@login_required
def api_quiz_words(group_id):
    group = StudyGroup.query.get_or_404(group_id)
    today_start_utc = get_tw_today_start_utc()
    
    # Get unique words studied today
    logs = VocabHistoryLog.query.filter(
        VocabHistoryLog.user_id == current_user.id,
        VocabHistoryLog.created_at >= today_start_utc
    ).all()
    studied_words = list({log.word for log in logs})
    
    # If they studied more than daily_goal, just pick daily_goal amount randomly, or test all of them.
    # The requirement is "對該天背的單字進行測驗". Testing all of them is fairer.
    # We need to fetch the definitions for these words.
    # Read from JSON
    import json
    try:
        from routes.vocab_routes import _load_vocab
        all_vocab = _load_vocab()
    except:
        all_vocab = []
        
    vocab_dict = {w['word'].lower(): w for w in all_vocab}
    
    quiz_pool = []
    for w in studied_words:
        w_lower = w.lower()
        if w_lower in vocab_dict:
            quiz_pool.append(vocab_dict[w_lower])
            
    # Shuffle
    random.shuffle(quiz_pool)
    
    return jsonify({'words': quiz_pool})

@group_bp.route('/<int:group_id>/api/submit_quiz', methods=['POST'])
@login_required
def submit_quiz(group_id):
    group = StudyGroup.query.get_or_404(group_id)
    data = request.json
    score = data.get('score', 0)
    
    today_str = get_tw_today_str()
    record = GroupDailyRecord.query.filter_by(group_id=group.id, user_id=current_user.id, date=today_str).first()
    
    if record:
        if not record.quiz_taken:
            record.quiz_score = score
            record.quiz_taken = True
            db.session.commit()
            return jsonify({'success': True, 'message': '成績已記錄！'})
        else:
            return jsonify({'success': True, 'message': '已完成過測驗，本次成績不計入排名。'})
            
    return jsonify({'success': False, 'error': '找不到記錄'})
