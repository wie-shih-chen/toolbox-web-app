"""
routes/vocab_routes.py
TOEIC 背單字模組 — 從本地 JSON 檔案讀取（離線模式，不依賴外部 API）
"""
import json
import os
from flask import Blueprint, render_template, request, jsonify, current_app, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, VocabProgress, UserSettings, VocabHistoryLog
from datetime import datetime

vocab_bp = Blueprint('vocab', __name__, template_folder='../templates')

# ─── 本地資料快取 ─────────────────────────────────────────────────
_vocab_cache = None

def _load_vocab():
    """載入本地 JSON 資料（只載入一次，快取在記憶體中）"""
    global _vocab_cache
    if _vocab_cache is None:
        json_path = os.path.join(current_app.root_path, 'static', 'data', 'toeic_vocabulary.json')
        with open(json_path, 'r', encoding='utf-8') as f:
            raw = json.load(f)
        # 統一欄位格式
        _vocab_cache = []
        for item in raw:
            _vocab_cache.append({
                'word':         item.get('english_word', ''),
                'definition':   item.get('chinese_definition', ''),
                'star':         item.get('star_rating', 0),
                'category':     item.get('category', ''),
                'score_range':  item.get('toeic_score_range', ''),
                'parts_of_speech': item.get('parts_of_speech', []),
                'word_forms':   item.get('word_forms', []),
                'examples':     item.get('examples', []),
                'exam_tips':    item.get('exam_tips', []),
            })
    return _vocab_cache


# ─── 頁面路由 ────────────────────────────────────────────────────
@vocab_bp.route('/')
@login_required
def index():
    """學習中心主頁"""
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
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
    
    try:
        all_words = _load_vocab()
        total_words = len(all_words)
    except Exception:
        total_words = 11238
    
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
    # 找出使用者所有的歷史紀錄，並依日期分組
    logs = VocabHistoryLog.query.filter_by(user_id=current_user.id).order_by(VocabHistoryLog.created_at.desc()).all()
    
    history_data = {}
    for log in logs:
        # local time representation via UTC
        date_str = log.created_at.strftime('%Y-%m-%d')
        if date_str not in history_data:
            history_data[date_str] = {'correct': 0, 'incorrect': 0, 'words': {}}
            
        history_data[date_str][log.result] += 1
        
        # Keep track of words studied this day
        if log.word not in history_data[date_str]['words']:
            history_data[date_str]['words'][log.word] = {'correct': 0, 'incorrect': 0}
        history_data[date_str]['words'][log.word][log.result] += 1
        
    return render_template('vocab/history.html', history_data=history_data)

@vocab_bp.route('/api/reset_progress', methods=['POST'])
@login_required
def reset_progress():
    """
    刪除該使用者的所有背單字進度與歷史紀錄
    """
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
    """
    從本地 JSON 提供單字資料
    QueryParams: offset, length, star, category, score_range
    """
    offset   = request.args.get('offset', 0, type=int)
    length   = request.args.get('length', 100, type=int)
    star_f   = request.args.get('star', type=int)
    cat_f    = request.args.get('category', '').strip()
    score_f  = request.args.get('score_range', '').strip()
    search_q = request.args.get('search', '').strip().lower()
    
    review_date = request.args.get('review_date', '').strip()
    
    try:
        all_words = _load_vocab()
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    # 歷史複習過濾
    if review_date:
        logs = VocabHistoryLog.query.filter_by(user_id=current_user.id).all()
        reviewed_words = {log.word for log in logs if log.created_at.strftime('%Y-%m-%d') == review_date}
        all_words = [w for w in all_words if w['word'] in reviewed_words]
    
    # 常規過濾
    filtered = all_words
    if star_f:
        filtered = [w for w in filtered if w['star'] == star_f]
    if cat_f:
        filtered = [w for w in filtered if cat_f in w['category']]
    if score_f:
        filtered = [w for w in filtered if score_f in w['score_range']]
    if search_q:
        import re
        if re.match(r'^[a-z0-9\s\-]+$', search_q):
            # 如果搜尋字串只有英文/數字，則只精確比對「英文單字字首」
            filtered = [w for w in filtered if w['word'].lower().startswith(search_q)]
        else:
            # 如果包含中文或其他字元，則只在「中文解釋」中尋找
            filtered = [w for w in filtered if search_q in w.get('definition', '').lower()]
    
    total = len(filtered)
    page  = filtered[offset:offset + length]
    
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
    
    # 新增歷史紀錄
    history_log = VocabHistoryLog(user_id=current_user.id, word=word, result=result)
    db.session.add(history_log)
    
    db.session.commit()
    
    return jsonify({'ok': True, 'correct': record.correct, 'incorrect': record.incorrect})


@vocab_bp.route('/api/lookup')
@login_required
def api_lookup():
    """
    GET /vocab/api/lookup?word=resume
    從官方字庫精確比對單一單字，回傳完整資料
    """
    word = request.args.get('word', '').strip().lower()
    if not word:
        return jsonify({'found': False}), 400
    try:
        all_words = _load_vocab()
    except Exception as e:
        return jsonify({'found': False, 'error': str(e)}), 500

    for w in all_words:
        if w['word'].lower() == word:
            return jsonify({'found': True, 'word': w})
    return jsonify({'found': False})


@vocab_bp.route('/api/batch_lookup', methods=['POST'])
@login_required
def api_batch_lookup():
    """
    POST /vocab/api/batch_lookup  body: {"words": ["resume","opening",...]}
    批量比對多個單字是否在官方字庫中，回傳 {word: bool} 的對應表
    """
    body = request.get_json()
    query_words = [w.strip().lower() for w in (body.get('words') or []) if w]
    if not query_words:
        return jsonify({})
    try:
        all_words = _load_vocab()
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    official_set = {w['word'].lower() for w in all_words}
    result = {qw: (qw in official_set) for qw in query_words}
    return jsonify(result)


@vocab_bp.route('/api/stats')
@login_required
def api_stats():
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
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
