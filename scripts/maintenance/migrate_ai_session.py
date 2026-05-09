"""
遷移腳本：建立 line_conversation_sessions 資料表
用於 AI 對話管家的多輪對話狀態儲存。

執行方式：
  python3 scripts/maintenance/migrate_ai_session.py
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import app, db
from models import LineConversationSession

with app.app_context():
    try:
        db.create_all()
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        if 'line_conversation_sessions' in tables:
            print("✅ line_conversation_sessions 資料表建立成功！")
        else:
            print("⚠️ 資料表未找到，請確認 models.py 是否正確。")
    except Exception as e:
        print(f"❌ 遷移失敗：{e}")
        sys.exit(1)
