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

def apply_vocab_pipeline(group, words_list, pipeline_config):
    if not pipeline_config:
        random.shuffle(words_list)
        return words_list

    current_list = list(words_list)
    
    for block in pipeline_config:
        b_type = block.get('type')
        b_val = block.get('value')
        
        if b_type == 'exclude_learned':
            past = GroupDailyAssignment.query.filter_by(group_id=group.id).all()
            past_words = set()
            for p in past:
                w_list = json.loads(p.words_json)
                for w in w_list:
                    past_words.add(w['word'])
            current_list = [w for w in current_list if w['word'] not in past_words]
            
        elif b_type == 'score':
            score_order = {'0-400': 1, '400-600': 2, '600-780': 3, '780-900': 4, '900+': 5}
            if b_val == 'sort_asc':
                current_list.sort(key=lambda x: score_order.get(x.get('score_range', ''), 0))
            elif b_val == 'sort_desc':
                current_list.sort(key=lambda x: score_order.get(x.get('score_range', ''), 0), reverse=True)
            elif isinstance(b_val, list) and len(b_val) > 0:
                current_list = [w for w in current_list if w.get('score_range') in b_val]
                
        elif b_type == 'star':
            if b_val == 'sort_asc':
                current_list.sort(key=lambda x: int(x.get('star', 0)))
            elif b_val == 'sort_desc':
                current_list.sort(key=lambda x: int(x.get('star', 0)), reverse=True)
            elif isinstance(b_val, list) and len(b_val) > 0:
                stars = [int(v) for v in b_val]
                current_list = [w for w in current_list if int(w.get('star', 0)) in stars]
                
        elif b_type == 'category':
            if isinstance(b_val, list) and len(b_val) > 0:
                current_list = [w for w in current_list if w.get('category') in b_val]
                
        elif b_type == 'pos':
            if isinstance(b_val, list) and len(b_val) > 0:
                current_list = [w for w in current_list if any(p in b_val for p in w.get('parts_of_speech', []))]
                
        elif b_type == 'shuffle':
            random.shuffle(current_list)

    return current_list

def get_or_create_daily_assignment(group, date_str):
    assignment = GroupDailyAssignment.query.filter_by(group_id=group.id, date=date_str).first()
    if not assignment:
        all_words = _load_vocab()
        
        unique_words_list = []
        seen = set()
        for w in all_words:
            if w['word'] not in seen:
                seen.add(w['word'])
                unique_words_list.append(w)
                
        pipeline_config = None
        if group.vocab_filter_config:
            try:
                pipeline_config = json.loads(group.vocab_filter_config)
            except Exception:
                pass
                
        filtered_words = apply_vocab_pipeline(group, unique_words_list, pipeline_config)
        
        num_words = min(group.daily_goal, len(filtered_words))
        # Since pipeline might have sorted it, we just take the first N elements!
        # If it's pure random, apply_vocab_pipeline already shuffled it or we can just take the first N.
        selected_words = filtered_words[:num_words] if num_words > 0 else []
        
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

@group_bp.route('/<int:group_id>/delete', methods=['POST'])
@login_required
def delete_group(group_id):
    group = StudyGroup.query.get_or_404(group_id)
    
    if group.owner_id != current_user.id:
        flash('只有群組建立者可以刪除群組！', 'error')
        return redirect(url_for('group.dashboard', group_id=group.id))
        
    source_name = f'group_{group.id}'
    
    try:
        # Delete related data
        GroupMember.query.filter_by(group_id=group.id).delete()
        GroupDailyRecord.query.filter_by(group_id=group.id).delete()
        GroupDailyAssignment.query.filter_by(group_id=group.id).delete()
        
        # Delete related vocab progress and history
        VocabProgress.query.filter_by(source=source_name).delete()
        VocabHistoryLog.query.filter_by(source=source_name).delete()
        
        # Delete the group itself
        db.session.delete(group)
        db.session.commit()
        flash(f'群組「{group.name}」已成功刪除。', 'success')
    except Exception as e:
        db.session.rollback()
        flash('刪除群組時發生錯誤，請稍後再試。', 'error')
        
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
        
        assignment = get_or_create_daily_assignment(group, today_str)
        assignment_words = {w['word'] for w in assignment}
        
        # If user has studied all unique words in today's assignment, they reached the goal.
        if len(assignment_words) > 0 and unique_words.issuperset(assignment_words):
            record.words_studied = group.daily_goal
        elif len(unique_words) > (record.words_studied or 0):
            record.words_studied = len(unique_words)
        db.session.commit()
        
        # Calculate all-time group stats for this user
        all_time = VocabProgress.query.filter_by(
            user_id=user.id,
            source=f'group_{group.id}'
        ).all()
        
        total_vocab = len(all_time)
        
        # Calculate overall accuracy based on QUIZ scores, not study progress
        all_quizzes = GroupDailyRecord.query.filter_by(group_id=group.id, user_id=user.id, quiz_taken=True).all()
        if all_quizzes:
            accuracy = round(sum(q.quiz_score for q in all_quizzes) / len(all_quizzes))
        else:
            accuracy = None
        
        # Calculate past 7 days accuracy for chart
        tw_now = datetime.utcnow() + timedelta(hours=8)
        start_date = tw_now - timedelta(days=6)
        start_utc = start_date.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(hours=8)
        
        # Use quiz_score from GroupDailyRecord for the line chart
        recent_records = GroupDailyRecord.query.filter(
            GroupDailyRecord.group_id == group.id,
            GroupDailyRecord.user_id == user.id,
            GroupDailyRecord.date >= (tw_now - timedelta(days=6)).strftime('%Y-%m-%d')
        ).all()
        
        record_dict = {r.date: r.quiz_score for r in recent_records if r.quiz_taken}
        
        chart_labels = []
        chart_data = []
        for i in range(6, -1, -1):
            day_obj = tw_now - timedelta(days=i)
            day_str = day_obj.strftime('%m/%d')
            full_date_str = day_obj.strftime('%Y-%m-%d')
            
            chart_labels.append(day_str)
            if full_date_str in record_dict:
                chart_data.append(record_dict[full_date_str])
            else:
                chart_data.append(0)
        
        data = {
            'user': user,
            'record': record,
            'is_me': user.id == current_user.id,
            'total_vocab': total_vocab,
            'accuracy': accuracy,
            'chart_labels': chart_labels,
            'chart_data': chart_data
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
        
    date_str = request.args.get('date') or get_tw_today_str()
    record = GroupDailyRecord.query.filter_by(group_id=group.id, user_id=current_user.id, date=date_str).first()
    
    if not record or record.words_studied < group.daily_goal:
        flash(f'必須先背滿 {group.daily_goal} 個單字才能開始測驗喔！', 'warning')
        return redirect(url_for('group.dashboard', group_id=group.id))
        
    return render_template('vocab/group_quiz.html', group=group, record=record, date=date_str)

@group_bp.route('/<int:group_id>/study')
@login_required
def group_study(group_id):
    group = StudyGroup.query.get_or_404(group_id)
    member = GroupMember.query.filter_by(group_id=group.id, user_id=current_user.id).first()
    if not member:
        return redirect(url_for('group.index'))
        
    date_str = request.args.get('date') or get_tw_today_str()
    # Get or create daily record
    record = GroupDailyRecord.query.filter_by(group_id=group.id, user_id=current_user.id, date=date_str).first()
    if not record:
        record = GroupDailyRecord(group_id=group.id, user_id=current_user.id, date=date_str)
        db.session.add(record)
        db.session.commit()

    assignment = get_or_create_daily_assignment(group, date_str)
    
    return render_template('vocab/group_study.html', group=group, record=record, words=assignment, date=date_str)

@group_bp.route('/<int:group_id>/history')
@login_required
def group_history(group_id):
    group = StudyGroup.query.get_or_404(group_id)
    member = GroupMember.query.filter_by(group_id=group.id, user_id=current_user.id).first()
    if not member:
        return redirect(url_for('group.index'))
    tw_now = datetime.utcnow() + timedelta(hours=8)
    group_tw_created = group.created_at + timedelta(hours=8)
    start_date = group_tw_created.date()
    end_date = tw_now.date()
    
    # Cap at 14 days maximum to avoid too long a page
    if (end_date - start_date).days > 14:
        start_date = end_date - timedelta(days=14)
        
    history_data = []
    
    current_date = end_date
    while current_date >= start_date:
        date_str = current_date.strftime('%Y-%m-%d')
        
        assignment = GroupDailyAssignment.query.filter_by(group_id=group.id, date=date_str).first()
        if assignment:
            record = GroupDailyRecord.query.filter_by(group_id=group.id, user_id=current_user.id, date=date_str).first()
            
            # Fetch VocabProgress for these words
            import json
            words_list = json.loads(assignment.words_json) if isinstance(assignment.words_json, str) else assignment.words_json
            word_strings = [w['word'] for w in words_list]
            
            vps = VocabProgress.query.filter(
                VocabProgress.user_id == current_user.id,
                VocabProgress.source == f'group_{group.id}',
                VocabProgress.word.in_(word_strings)
            ).all()
            
            vp_dict = {vp.word: vp for vp in vps}
            
            # Decorate words
            decorated_words = []
            for w in words_list:
                word_str = w['word']
                vp = vp_dict.get(word_str)
                decorated_words.append({
                    'word': word_str,
                    'translation': w.get('definition', ''),
                    'correct': vp.correct if vp else 0,
                    'incorrect': vp.incorrect if vp else 0
                })
                
            history_data.append({
                'date': date_str,
                'record': record,
                'words': decorated_words
            })
            
        current_date -= timedelta(days=1)
        
    today_str = get_tw_today_str()
    return render_template('vocab/group_history.html', group=group, history_data=history_data, today_str=today_str)

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
    date_str = data.get('date') or get_tw_today_str()
    
    record = GroupDailyRecord.query.filter_by(group_id=group.id, user_id=current_user.id, date=date_str).first()
    
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
    date_str = data.get('date') or get_tw_today_str()
    index = data.get('index', -1)
    
    if not word or result not in ['correct', 'incorrect']:
        return jsonify({'error': 'Invalid data'}), 400
        
    source = f'group_{group.id}'
    
    # Update VocabProgress for this group
    vp = VocabProgress.query.filter_by(user_id=current_user.id, word=word, source=source).first()
    if not vp:
        vp = VocabProgress(user_id=current_user.id, word=word, source=source, correct=0, incorrect=0)
        db.session.add(vp)
        
    if result == 'correct':
        vp.correct = (vp.correct or 0) + 1
    else:
        vp.incorrect = (vp.incorrect or 0) + 1
    vp.last_reviewed = datetime.utcnow()
    
    # Add history log
    log = VocabHistoryLog(user_id=current_user.id, word=word, result=result, source=source)
    db.session.add(log)
    
    # Update words_studied to index + 1 if necessary
    if index >= 0:
        record = GroupDailyRecord.query.filter_by(group_id=group.id, user_id=current_user.id, date=date_str).first()
        if record and record.words_studied < index + 1:
            record.words_studied = index + 1
            
    db.session.commit()
    return jsonify({'success': True})

@group_bp.route('/<int:group_id>/api/mark_studied', methods=['POST'])
@login_required
def api_mark_studied(group_id):
    group = StudyGroup.query.get_or_404(group_id)
    data = request.json or {}
    date_str = data.get('date') or get_tw_today_str()
    record = GroupDailyRecord.query.filter_by(group_id=group.id, user_id=current_user.id, date=date_str).first()
    
    if record:
        # User finished flipping all flashcards for today
        record.words_studied = group.daily_goal
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'error': 'Record not found'}), 404

@group_bp.route('/<int:group_id>/settings', methods=['POST'])
@login_required
def update_settings(group_id):
    group = StudyGroup.query.get_or_404(group_id)
    if group.owner_id != current_user.id:
        flash('只有群主可以修改設定！', 'danger')
        return redirect(url_for('group.dashboard', group_id=group.id))
        
    new_goal = request.form.get('daily_goal', type=int)
    new_name = request.form.get('name', '').strip()
    vocab_filter_config = request.form.get('vocab_filter_config')
    
    settings_changed = False
    
    if new_name and group.name != new_name:
        group.name = new_name
        
    if vocab_filter_config is not None and group.vocab_filter_config != vocab_filter_config:
        group.vocab_filter_config = vocab_filter_config
        settings_changed = True
        
    if new_goal and 5 <= new_goal <= 100 and group.daily_goal != new_goal:
        group.daily_goal = new_goal
        settings_changed = True
        
    if settings_changed:
        # Clear today's assignment to apply changes immediately
        today_str = get_tw_today_str()
        GroupDailyAssignment.query.filter_by(group_id=group.id, date=today_str).delete()
        
    if new_goal and 5 <= new_goal <= 100:
        db.session.commit()
        flash('群組設定已更新！', 'success')
    else:
        db.session.commit()
        if not new_goal or new_goal < 5 or new_goal > 100:
            flash('設定已儲存，但每日目標必須在 5 到 100 之間！', 'warning')
        else:
            flash('群組設定已更新！', 'success')
            
    return redirect(url_for('group.dashboard', group_id=group.id))

@group_bp.route('/<int:group_id>/api/filter_preview', methods=['POST'])
@login_required
def api_filter_preview(group_id):
    group = StudyGroup.query.get_or_404(group_id)
    pipeline_config = request.json.get('pipeline', [])
    
    all_words = _load_vocab()
    unique_words_list = []
    seen = set()
    for w in all_words:
        if w['word'] not in seen:
            seen.add(w['word'])
            unique_words_list.append(w)
            
    filtered_words = apply_vocab_pipeline(group, unique_words_list, pipeline_config)
    
    return jsonify({
        'success': True,
        'count': len(filtered_words)
    })

@group_bp.route('/<int:group_id>/api/reset_history', methods=['POST'])
@login_required
def api_reset_history(group_id):
    group = StudyGroup.query.get_or_404(group_id)
    if group.owner_id != current_user.id:
        return jsonify({'error': '只有群主可以重置紀錄！'}), 403
        
    # Delete all assignments for this group
    GroupDailyAssignment.query.filter_by(group_id=group.id).delete()
    db.session.commit()
    
    return jsonify({'success': True})

@group_bp.route('/<int:group_id>/api/clear_all_records', methods=['POST'])
@login_required
def api_clear_all_records(group_id):
    group = StudyGroup.query.get_or_404(group_id)
    if group.owner_id != current_user.id:
        return jsonify({'error': '只有群主可以清除所有紀錄！'}), 403
        
    source_name = f'group_{group.id}'
    
    GroupDailyAssignment.query.filter_by(group_id=group.id).delete()
    GroupDailyRecord.query.filter_by(group_id=group.id).delete()
    VocabHistoryLog.query.filter_by(source=source_name).delete()
    VocabProgress.query.filter_by(source=source_name).delete()
    
    group.vocab_filter_config = None
    group.daily_goal = 20
    
    db.session.commit()
    
    return jsonify({'success': True})
