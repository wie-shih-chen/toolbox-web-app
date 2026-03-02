"""
【狀態】已執行過，通常不需要再跑。

【使用時機】
  若 user_settings 資料表缺少 LINE Bot 相關欄位時執行。
  新增欄位：user_settings 資料表
    - line_user_id         LINE 用戶 ID（綁定後填入）
    - binding_code         綁定驗證碼（6位數）
    - binding_expiry       驗證碼到期時間
    - notification_methods 通知方式（JSON，預設 ["email"]）

【執行方式】
  cd ~/toolbox-web-app
  source venv/bin/activate
  python scripts/maintenance/migrate_line_bot_v5.py

【依賴】
  需要 Flask 虛擬環境。
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import app, db
from models import UserSettings
from sqlalchemy import text

def migrate():
    with app.app_context():
        print("Starting migration v5: Add LINE Bot fields...")
        
        inspector = db.inspect(db.engine)
        columns = [c['name'] for c in inspector.get_columns('user_settings')]
        
        try:
            with db.engine.connect() as conn:
                if 'line_user_id' not in columns:
                    print("Adding line_user_id...")
                    conn.execute(text("ALTER TABLE user_settings ADD COLUMN line_user_id VARCHAR(255)"))
                
                if 'binding_code' not in columns:
                    print("Adding binding_code...")
                    conn.execute(text("ALTER TABLE user_settings ADD COLUMN binding_code VARCHAR(6)"))
                
                if 'binding_expiry' not in columns:
                    print("Adding binding_expiry...")
                    conn.execute(text("ALTER TABLE user_settings ADD COLUMN binding_expiry DATETIME"))
                
                if 'notification_methods' not in columns:
                    print("Adding notification_methods...")
                    conn.execute(text("ALTER TABLE user_settings ADD COLUMN notification_methods TEXT DEFAULT '[\"email\"]'"))
                
                conn.commit()
                
            print("Migration v5 completed successfully!")
            
        except Exception as e:
            print(f"Migration failed: {e}")

if __name__ == "__main__":
    migrate()
