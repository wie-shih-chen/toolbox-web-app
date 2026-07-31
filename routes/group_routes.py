import os
import random
import string
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from models import db, User, StudyGroup, GroupMember, GroupDailyRecord, VocabHistoryLog, VocabProgress, GroupDailyAssignment
import json
from routes.vocab_routes import _load_vocab

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

def get_or_create_daily_assignment(group, date_str):
    assignment = GroupDailyAssignment.query.filter_by(group_id=group.id, date=date_str).first()
    if not assignment:
        all_words = _load_vocab()
        # Ensure we have enough words
        num_words = min(group.daily_goal, len(all_words))
        selected_words = random.sample(all_words, num_words) if num_words > 0 else []
        assignment = GroupDailyAssignment(
            group_id=group.id,
            date=date_str,
            words_json=json.dumps(selected_words, ensure_ascii=False)
        )
        db.session.add(assignment)
        db.session.commit()
    return json.loads(assignment.words_json)

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
            
        # Count words studied in group today
        # Only count logs from this specific group source
        logs = VocabHistoryLog.query.filter(
            VocabHistoryLog.user_id == user.id,
            VocabHistoryLog.source == f'group_{group.id}',
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

@group_bp.route('/<int:group_id>/study')
@login_required
def group_study(group_id):
    group = StudyGroup.query.get_or_404(group_id)
    member = GroupMember.query.filter_by(group_id=group.id, user_id=current_user.id).first()
    if not member:
        return redirect(url_for('group.index'))
        
    today_str = get_tw_today_str()
    # Get or create daily record
    record = GroupDailyRecord.query.filter_by(group_id=group.id, user_id=current_user.id, date=today_str).first()
    if not record:
        record = GroupDailyRecord(group_id=group.id, user_id=current_user.id, date=today_str)
        db.session.add(record)
        db.session.commit()

    assignment = get_or_create_daily_assignment(group, today_str)
    
    return render_template('vocab/group_study.html', group=group, record=record, words=assignment)

@group_bp.route('/<int:group_id>/history')
@login_required
def group_history(group_id):
    group = StudyGroup.query.get_or_404(group_id)
    member = GroupMember.query.filter_by(group_id=group.id, user_id=current_user.id).first()
    if not member:
        return redirect(url_for('group.index'))
        
    # Get logs from this group
    logs = VocabHistoryLog.query.filter_by(
        user_id=current_user.id,
        source=f'group_{group.id}'
    ).order_by(VocabHistoryLog.created_at.desc()).all()
    
    history_data = {}
    for log in logs:
        # Convert UTC to local time (UTC+8)
        local_time = log.created_at + timedelta(hours=8)
        date_str = local_time.strftime('%Y-%m-%d')
        if date_str not in history_data:
            history_data[date_str] = {'correct': 0, 'incorrect': 0, 'words': {}}
            
        history_data[date_str][log.result] += 1
        
        # Keep track of words studied this day
        if log.word not in history_data[date_str]['words']:
            history_data[date_str]['words'][log.word] = {'correct': 0, 'incorrect': 0}
        history_data[date_str]['words'][log.word][log.result] += 1
        
    return render_template('vocab/group_history.html', group=group, history_data=history_data)

@group_bp.route('/<int:group_id>/api/quiz_words')
@login_required
def api_quiz_words(group_id):
    group = StudyGroup.query.get_or_404(group_id)
    today_str = get_tw_today_str()
    
    # Get today's assignment
    assignment = get_or_create_daily_assignment(group, today_str)
    
    # The assignment is already a list of word dictionaries
    quiz_pool = assignment.copy()
            
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

@group_bp.route('/<int:group_id>/api/update_progress', methods=['POST'])
@login_required
def update_progress(group_id):
    group = StudyGroup.query.get_or_404(group_id)
    data = request.json
    word = data.get('word')
    result = data.get('result')  # 'correct' or 'incorrect'
    
    if not word or result not in ['correct', 'incorrect']:
        return jsonify({'error': 'Invalid data'}), 400
        
    source = f'group_{group.id}'
    
    # Update VocabProgress for this group
    vp = VocabProgress.query.filter_by(user_id=current_user.id, word=word, source=source).first()
    if not vp:
        vp = VocabProgress(user_id=current_user.id, word=word, source=source)
        db.session.add(vp)
        
    if result == 'correct':
        vp.correct += 1
    else:
        vp.incorrect += 1
    vp.last_reviewed = datetime.utcnow()
    
    # Add history log
    log = VocabHistoryLog(user_id=current_user.id, word=word, result=result, source=source)
    db.session.add(log)
    
    db.session.commit()
    return jsonify({'success': True})

@group_bp.route('/<int:group_id>/api/mark_studied', methods=['POST'])
@login_required
def api_mark_studied(group_id):
    group = StudyGroup.query.get_or_404(group_id)
    today_str = get_tw_today_str()
    record = GroupDailyRecord.query.filter_by(group_id=group.id, user_id=current_user.id, date=today_str).first()
    
    if record:
        # User finished flipping all flashcards for today
        record.words_studied = group.daily_goal
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': '找不到記錄'})
