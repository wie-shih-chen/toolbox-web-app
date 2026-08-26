"""
services/sqlite_service.py
以 SQLite 取代 MongoDB，讀取本地 master_vocabulary.db 進行單字查詢
資料庫格式：vocabulary(english_word TEXT PRIMARY KEY, details_json TEXT)
"""
import sqlite3
import json
import os
import logging
import re

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'master_vocabulary.db')


def _get_conn():
    db_path = os.path.abspath(DB_PATH)
    if not os.path.exists(db_path):
        logging.error(f"SQLite vocabulary DB not found at {db_path}")
        return None
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _row_to_word(row):
    """把 SQLite 的 row 轉成前端用的 dict"""
    details = json.loads(row['details_json'])
    return {
        'word':            details.get('english_word', row['english_word']),
        'definition':      details.get('chinese_definition', ''),
        'star':            details.get('star_rating', 0),
        'category':        details.get('category', ''),
        'score_range':     details.get('toeic_score_range', ''),
        'parts_of_speech': details.get('parts_of_speech', []),
        'word_forms':      details.get('word_forms', []),
        'examples':        details.get('examples', []),
        'exam_tips':       details.get('exam_tips', []),
    }


def count_words(filters=None):
    """計算符合過濾條件的單字數量"""
    conn = _get_conn()
    if not conn:
        return 0
    filters = filters or {}
    where, params = _build_where(filters)
    sql = f"SELECT COUNT(*) FROM vocabulary {where}"
    try:
        cur = conn.execute(sql, params)
        return cur.fetchone()[0]
    except Exception as e:
        logging.error(f"count_words error: {e}")
        return 0
    finally:
        conn.close()


def get_words(filters=None, offset=0, limit=100):
    """取得符合過濾條件的單字列表"""
    conn = _get_conn()
    if not conn:
        return []
    filters = filters or {}
    where, params = _build_where(filters)
    sql = f"SELECT english_word, details_json FROM vocabulary {where} LIMIT ? OFFSET ?"
    params += [limit, offset]
    try:
        cur = conn.execute(sql, params)
        return [_row_to_word(r) for r in cur.fetchall()]
    except Exception as e:
        logging.error(f"get_words error: {e}")
        return []
    finally:
        conn.close()


def get_word(word):
    """精確查詢單一單字"""
    conn = _get_conn()
    if not conn:
        return None
    sql = "SELECT english_word, details_json FROM vocabulary WHERE LOWER(english_word) = ?"
    try:
        cur = conn.execute(sql, [word.lower()])
        row = cur.fetchone()
        return _row_to_word(row) if row else None
    except Exception as e:
        logging.error(f"get_word error: {e}")
        return None
    finally:
        conn.close()


def get_words_in(word_list):
    """批量查詢多個單字（回傳 set）"""
    if not word_list:
        return set()
    conn = _get_conn()
    if not conn:
        return set()
    placeholders = ','.join(['?' for _ in word_list])
    sql = f"SELECT LOWER(english_word) FROM vocabulary WHERE LOWER(english_word) IN ({placeholders})"
    try:
        cur = conn.execute(sql, [w.lower() for w in word_list])
        return {row[0] for row in cur.fetchall()}
    except Exception as e:
        logging.error(f"get_words_in error: {e}")
        return set()
    finally:
        conn.close()


def get_all_words():
    """取得所有單字（給 group_routes 用，注意回傳量較大）"""
    conn = _get_conn()
    if not conn:
        return []
    try:
        cur = conn.execute("SELECT english_word, details_json FROM vocabulary")
        return [_row_to_word(r) for r in cur.fetchall()]
    except Exception as e:
        logging.error(f"get_all_words error: {e}")
        return []
    finally:
        conn.close()


def _build_where(filters):
    """依 filters dict 建立 WHERE 子句與參數"""
    conditions = []
    params = []

    star = filters.get('star')
    if star:
        conditions.append("json_extract(details_json, '$.star_rating') = ?")
        params.append(int(star))

    category = filters.get('category', '').strip()
    if category:
        conditions.append("json_extract(details_json, '$.category') LIKE ?")
        params.append(f'%{category}%')

    score_range = filters.get('score_range', '').strip()
    if score_range:
        conditions.append("json_extract(details_json, '$.toeic_score_range') LIKE ?")
        params.append(f'%{score_range}%')

    search = filters.get('search', '').strip().lower()
    if search:
        if re.match(r'^[a-z0-9\s\-]+$', search):
            conditions.append("LOWER(english_word) LIKE ?")
            params.append(f'{search}%')
        else:
            conditions.append("json_extract(details_json, '$.chinese_definition') LIKE ?")
            params.append(f'%{search}%')

    in_words = filters.get('in_words')
    if in_words:
        placeholders = ','.join(['?' for _ in in_words])
        conditions.append(f"LOWER(english_word) IN ({placeholders})")
        params += [w.lower() for w in in_words]

    where = ('WHERE ' + ' AND '.join(conditions)) if conditions else ''
    return where, params
