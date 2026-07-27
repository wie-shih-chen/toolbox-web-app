"""
routes/vocab_routes.py
TOEIC 背單字模組 — 包含 HuggingFace proxy API 與學習進度 CRUD
"""
import requests
from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from flask_login import login_required, current_user
from models import db, VocabProgress
from datetime import datetime, date

vocab_bp = Blueprint('vocab', __name__, template_folder='../templates')

# ─── HuggingFace Dataset Viewer API ─────────────────────────────
HF_API = "https://datasets-server.huggingface.co/rows"
HF_DATASET = "kknono668/toeic-vocab-tw"
HF_CONFIG = "default"
HF_SPLIT = "train"


# ─── 頁面路由 ────────────────────────────────────────────────────
@vocab_bp.route('/')
@login_required
def index():
    """學習中心主頁"""
    # 取得今日日期的學習統計
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
    
    # 每日目標（預設 20 個）
    daily_goal = 20
    
    stats = {
        'today_reviewed': today_reviewed,
        'daily_goal': daily_goal,
        'daily_progress_pct': min(round(today_reviewed / daily_goal * 100), 100),
        'total_seen': total_seen,
        'correct_sum': correct_sum,
        'incorrect_sum': incorrect_sum,
        'overall_accuracy': overall_accuracy,
    }
    
    return render_template('vocab/index.html', stats=stats)


@vocab_bp.route('/browse')
@login_required
def browse():
    """瀏覽模式"""
    return render_template('vocab/browse.html')


@vocab_bp.route('/flashcard')
@login_required
def flashcard():
    """卡片翻轉模式"""
    return render_template('vocab/flashcard.html')


@vocab_bp.route('/quiz')
@login_required
def quiz():
    """選擇題模式"""
    return render_template('vocab/quiz.html')


@vocab_bp.route('/spelling')
@login_required
def spelling():
    """拼字測驗模式"""
    return render_template('vocab/spelling.html')


# ─── API 路由 ────────────────────────────────────────────────────
@vocab_bp.route('/api/words')
@login_required
def api_words():
    """
    HuggingFace Dataset API Proxy — 轉發並回傳單字資料 (JSON)
    QueryParams: offset, length, star, category, score_range
    """
    offset = request.args.get('offset', 0, type=int)
    length = request.args.get('length', 100, type=int)
    
    params = {
        'dataset': HF_DATASET,
        'config': HF_CONFIG,
        'split': HF_SPLIT,
        'offset': offset,
        'length': min(length, 100),  # HF API 最多 100 筆
    }
    
    try:
        resp = requests.get(HF_API, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        return jsonify({'error': str(e)}), 503
    
    # 取出 rows 並整理欄位
    rows = data.get('rows', [])
    words = []
    
    # 前端過濾條件（HF API 不支援 server-side filter for this dataset）
    star_filter = request.args.get('star', type=int)
    category_filter = request.args.get('category', '')
    score_filter = request.args.get('score_range', '')
    
    # 取得使用者進度 map {word: VocabProgress}
    user_words = {vp.word: vp for vp in VocabProgress.query.filter_by(user_id=current_user.id).all()}
    
    for row in rows:
        r = row.get('row', {})
        word = r.get('english_word', '')
        star = r.get('star_rating', 0)
        category = r.get('category', '')
        score_range = r.get('toeic_score_range', '')
        
        # 套用前端過濾
        if star_filter and star != star_filter:
            continue
        if category_filter and category_filter not in category:
            continue
        if score_filter and score_filter not in score_range:
            continue
        
        # 取得使用者進度
        progress = user_words.get(word)
        
        words.append({
            'word': word,
            'definition': r.get('chinese_definition', ''),
            'star': star,
            'category': category,
            'score_range': score_range,
            'parts_of_speech': r.get('parts_of_speech', []),
            'word_forms': r.get('word_forms', []),
            'examples': r.get('examples', []),
            'exam_tips': r.get('exam_tips', []),
            'progress': {
                'correct': progress.correct if progress else 0,
                'incorrect': progress.incorrect if progress else 0,
            }
        })
    
    return jsonify({
        'words': words,
        'total': data.get('num_rows_total', 0),
        'offset': offset,
        'length': len(words)
    })


@vocab_bp.route('/api/progress', methods=['GET'])
@login_required
def get_progress():
    """取得使用者所有學習進度"""
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
    """更新單字學習進度（答對或答錯）"""
    data = request.get_json()
    word = data.get('word', '').strip()
    result = data.get('result', '')  # 'correct' | 'incorrect'
    
    if not word or result not in ('correct', 'incorrect'):
        return jsonify({'ok': False, 'msg': '參數錯誤'}), 400
    
    # upsert
    record = VocabProgress.query.filter_by(
        user_id=current_user.id, word=word
    ).first()
    
    if not record:
        record = VocabProgress(user_id=current_user.id, word=word)
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
    """取得使用者統計資料（for AJAX 更新）"""
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
    
    return jsonify({
        'today_reviewed': today_reviewed,
        'daily_goal': 20,
        'total_seen': total_seen,
        'overall_accuracy': overall_accuracy,
        'correct_sum': correct_sum,
        'incorrect_sum': incorrect_sum,
    })
