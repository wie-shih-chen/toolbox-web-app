"""
routes/vocab_routes.py
TOEIC 背單字模組 — 從本地 JSON 檔案讀取（離線模式，不依賴外部 API）
"""
import json
import os
from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from models import db, VocabProgress
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
    daily_goal = 20
    
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
    return render_template('vocab/quiz.html')


@vocab_bp.route('/spelling')
@login_required
def spelling():
    return render_template('vocab/spelling.html')


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
    
    try:
        all_words = _load_vocab()
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    # 過濾
    filtered = all_words
    if star_f:
        filtered = [w for w in filtered if w['star'] == star_f]
    if cat_f:
        filtered = [w for w in filtered if cat_f in w['category']]
    if score_f:
        filtered = [w for w in filtered if score_f in w['score_range']]
    
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
    db.session.commit()
    
    return jsonify({'ok': True, 'correct': record.correct, 'incorrect': record.incorrect})


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
    
    return jsonify({
        'today_reviewed': today_reviewed,
        'daily_goal': 20,
        'total_seen': VocabProgress.query.filter_by(user_id=current_user.id).count(),
        'overall_accuracy': round(correct_sum / total_answers * 100) if total_answers > 0 else 0,
    })
