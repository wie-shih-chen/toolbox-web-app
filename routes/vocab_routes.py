"""
routes/vocab_routes.py
TOEIC 背單字模組 — 使用本地 SQLite 資料庫（master_vocabulary.db）
"""
import json
import os
from flask import Blueprint, render_template, request, jsonify, current_app, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, VocabProgress, UserSettings, VocabHistoryLog
from services import sqlite_service as vocab_db
from datetime import datetime
import re

vocab_bp = Blueprint('vocab', __name__, template_folder='../templates')


# ─── 頁面路由 ────────────────────────────────────────────────────
@vocab_bp.route('/')
@login_required
def index():
    """學習中心主頁"""
    from datetime import timedelta
    tw_now = datetime.utcnow() + timedelta(hours=8)
    tw_midnight = tw_now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_start = tw_midnight - timedelta(hours=8)
    
    today_reviewed = VocabProgress.query.filter(
        VocabProgress.user_id == current_user.id,
        VocabProgress.last_reviewed >= today_start
    ).count()
    
    total_seen = VocabProgress.query.filter_by(user_id=current_user.id).count()
    
    correct_sum = db.session.query(db.func.sum(VocabProgress.correct)).filter_by(
        user_id=current_user.id
    ).scalar() or 0
    
    incorrect_sum = db.session.query(db.func.sum(VocabProgress.incorrect)).filter_by(
        user_id=current_user.id
    ).scalar() or 0
    
    total_answers = correct_sum + incorrect_sum
    overall_accuracy = round(correct_sum / total_answers * 100) if total_answers > 0 else 0
    
    settings = UserSettings.query.filter_by(user_id=current_user.id).first()
    daily_goal = settings.vocab_daily_goal if settings else 20
    
    total_words = vocab_db.count_words()
    
    stats = {
        'today_reviewed': today_reviewed,
        'daily_goal': daily_goal,
        'daily_progress_pct': min(round(today_reviewed / daily_goal * 100), 100),
        'total_seen': total_seen,
        'correct_sum': correct_sum,
        'incorrect_sum': incorrect_sum,
        'overall_accuracy': overall_accuracy,
        'total_words': total_words,
    }
    return render_template('vocab/index.html', stats=stats)


@vocab_bp.route('/browse')
@login_required
def browse():
    return render_template('vocab/browse.html')


@vocab_bp.route('/flashcard')
@login_required
def flashcard():
    return render_template('vocab/flashcard.html')


@vocab_bp.route('/quiz')
@login_required
def quiz():
    settings = UserSettings.query.filter_by(user_id=current_user.id).first()
    daily_goal = settings.vocab_daily_goal if settings else 20
    return render_template('vocab/quiz.html', daily_goal=daily_goal)


@vocab_bp.route('/spelling')
@login_required
def spelling():
    settings = UserSettings.query.filter_by(user_id=current_user.id).first()
    daily_goal = settings.vocab_daily_goal if settings else 20
    return render_template('vocab/spelling.html', daily_goal=daily_goal)


@vocab_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    settings_obj = UserSettings.query.filter_by(user_id=current_user.id).first()
    if not settings_obj:
        settings_obj = UserSettings(user_id=current_user.id)
        db.session.add(settings_obj)
        db.session.commit()
        
    if request.method == 'POST':
        goal = request.form.get('vocab_daily_goal', type=int)
        if goal and goal > 0:
            settings_obj.vocab_daily_goal = goal
            db.session.commit()
            flash('設定已儲存', 'success')
        else:
            flash('無效的目標數字', 'error')
        return redirect(url_for('vocab.settings'))
        
    return render_template('vocab/settings.html', settings=settings_obj)


@vocab_bp.route('/history')
@login_required
def history():
    logs = VocabHistoryLog.query.filter_by(user_id=current_user.id).order_by(VocabHistoryLog.created_at.desc()).all()
    
    history_data = {}
    from datetime import timedelta
    for log in logs:
        local_time = log.created_at + timedelta(hours=8)
        date_str = local_time.strftime('%Y-%m-%d')
        if date_str not in history_data:
            history_data[date_str] = {'correct': 0, 'incorrect': 0, 'words': {}}
            
        history_data[date_str][log.result] += 1
        
        if log.word not in history_data[date_str]['words']:
            history_data[date_str]['words'][log.word] = {'correct': 0, 'incorrect': 0}
        history_data[date_str]['words'][log.word][log.result] += 1
        
    return render_template('vocab/history.html', history_data=history_data)

@vocab_bp.route('/api/reset_progress', methods=['POST'])
@login_required
def reset_progress():
    try:
        VocabProgress.query.filter_by(user_id=current_user.id).delete()
        VocabHistoryLog.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

# ─── API 路由 ────────────────────────────────────────────────────
@vocab_bp.route('/api/words')
@login_required
def api_words():
    offset   = request.args.get('offset', 0, type=int)
    length   = request.args.get('length', 100, type=int)
    star_f   = request.args.get('star', type=int)
    cat_f    = request.args.get('category', '').strip()
    score_f  = request.args.get('score_range', '').strip()
    search_q = request.args.get('search', '').strip().lower()
    review_date = request.args.get('review_date', '').strip()
    
    filters = {}
    
    # 歷史複習過濾
    if review_date:
        from datetime import timedelta
        logs = VocabHistoryLog.query.filter_by(user_id=current_user.id).all()
        reviewed_words = [log.word for log in logs if (log.created_at + timedelta(hours=8)).strftime('%Y-%m-%d') == review_date]
        if not reviewed_words:
            return jsonify({'words': [], 'total': 0, 'offset': offset, 'length': 0})
        filters['in_words'] = reviewed_words
    
    if star_f:
        filters['star'] = star_f
    if cat_f:
        filters['category'] = cat_f
    if score_f:
        filters['score_range'] = score_f
    if search_q:
        filters['search'] = search_q
    
    total = vocab_db.count_words(filters)
    page  = vocab_db.get_words(filters, offset=offset, limit=length)
    
    # 取得使用者進度 map
    user_progress = {
        vp.word: {'correct': vp.correct, 'incorrect': vp.incorrect}
        for vp in VocabProgress.query.filter_by(user_id=current_user.id).all()
    }
    
    for w in page:
        prog = user_progress.get(w['word'])
        w['progress'] = prog or {'correct': 0, 'incorrect': 0}
    
    return jsonify({'words': page, 'total': total, 'offset': offset, 'length': len(page)})


@vocab_bp.route('/api/progress', methods=['GET'])
@login_required
def get_progress():
    records = VocabProgress.query.filter_by(user_id=current_user.id).all()
    result = {}
    for r in records:
        result[r.word] = {
            'correct': r.correct,
            'incorrect': r.incorrect,
            'accuracy': r.accuracy,
            'last_reviewed': r.last_reviewed.isoformat()
        }
    return jsonify(result)


@vocab_bp.route('/api/progress', methods=['POST'])
@login_required
def update_progress():
    data   = request.get_json()
    word   = data.get('word', '').strip()
    result = data.get('result', '')
    
    if not word or result not in ('correct', 'incorrect'):
        return jsonify({'ok': False, 'msg': '參數錯誤'}), 400
    
    record = VocabProgress.query.filter_by(user_id=current_user.id, word=word).first()
    if not record:
        record = VocabProgress(user_id=current_user.id, word=word, correct=0, incorrect=0)
        db.session.add(record)
    
    if result == 'correct':
        record.correct += 1
    else:
        record.incorrect += 1
    record.last_reviewed = datetime.utcnow()
    
    history_log = VocabHistoryLog(user_id=current_user.id, word=word, result=result)
    db.session.add(history_log)
    
    db.session.commit()
    
    return jsonify({'ok': True, 'correct': record.correct, 'incorrect': record.incorrect})


@vocab_bp.route('/api/lookup')
@login_required
def api_lookup():
    word = request.args.get('word', '').strip().lower()
    if not word:
        return jsonify({'found': False}), 400

    w = vocab_db.get_word(word)
    if w:
        return jsonify({'found': True, 'word': w})
    return jsonify({'found': False})


@vocab_bp.route('/api/batch_lookup', methods=['POST'])
@login_required
def api_batch_lookup():
    body = request.get_json()
    query_words = [w.strip().lower() for w in (body.get('words') or []) if w]
    if not query_words:
        return jsonify({})

    official_set = vocab_db.get_words_in(query_words)
    result = {qw: (qw in official_set) for qw in query_words}
    return jsonify(result)


@vocab_bp.route('/api/stats')
@login_required
def api_stats():
    from datetime import timedelta
    tw_now = datetime.utcnow() + timedelta(hours=8)
    tw_midnight = tw_now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_start = tw_midnight - timedelta(hours=8)
    
    today_reviewed = VocabProgress.query.filter(
        VocabProgress.user_id == current_user.id,
        VocabProgress.last_reviewed >= today_start
    ).count()
    
    correct_sum = db.session.query(db.func.sum(VocabProgress.correct)).filter_by(user_id=current_user.id).scalar() or 0
    incorrect_sum = db.session.query(db.func.sum(VocabProgress.incorrect)).filter_by(user_id=current_user.id).scalar() or 0
    total_answers = correct_sum + incorrect_sum
    
    settings = UserSettings.query.filter_by(user_id=current_user.id).first()
    daily_goal = settings.vocab_daily_goal if settings else 20
    
    return jsonify({
        'today_reviewed': today_reviewed,
        'daily_goal': daily_goal,
        'total_seen': VocabProgress.query.filter_by(user_id=current_user.id).count(),
        'overall_accuracy': round(correct_sum / total_answers * 100) if total_answers > 0 else 0,
    })
