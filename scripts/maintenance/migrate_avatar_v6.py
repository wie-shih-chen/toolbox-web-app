"""
【狀態】已執行過，通常不需要再跑。

【使用時機】
  若 user 資料表缺少頭像欄位時執行（v6 更新：改用 preset/upload 雙模式）。
  新增欄位：user 資料表
    - avatar_type  頭像類型（'preset' | 'upload'）
    - avatar_val   頭像值（預設頭像ID 或 上傳路徑）

【執行方式】
  cd ~/toolbox-web-app
  source venv/bin/activate
  python scripts/maintenance/migrate_avatar_v6.py

【依賴】
  需要 Flask 虛擬環境。
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import app, db
from models import User
from sqlalchemy import text

def migrate():
    with app.app_context():
        with db.engine.connect() as conn:
            columns = conn.execute(text("PRAGMA table_info(user)")).fetchall()
            col_names = [col[1] for col in columns]
            
            if 'avatar_type' not in col_names:
                print("Adding avatar_type column...")
                conn.execute(text("ALTER TABLE user ADD COLUMN avatar_type TEXT DEFAULT 'preset'"))
                
            if 'avatar_val' not in col_names:
                print("Adding avatar_val column...")
                conn.execute(text("ALTER TABLE user ADD COLUMN avatar_val TEXT DEFAULT 'default'"))
                
            conn.commit()
            print("Migration completed.")

if __name__ == '__main__':
    migrate()
