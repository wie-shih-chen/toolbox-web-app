"""
【使用時機】
  全新部署環境時，執行此腳本建立所有資料庫資料表。
  例如：首次在 PythonAnywhere 部署，或資料庫被刪除需要重建時。

【執行方式】
  cd ~/toolbox-web-app
  python scripts/maintenance/init_db.py

【注意】
  需要 Flask app 環境（虛擬環境已啟用且所有套件安裝完畢）。
  執行後會呼叫 db.create_all()，建立所有 models.py 中定義的資料表。
"""
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))  # 回到專案根目錄
sys.path.append(parent_dir)

from app import app, db
from models import ReportLog

with app.app_context():
    print("Creating all database tables...")
    db.create_all()
    print("Done! Database tables should be ready.")
    
    try:
        count = ReportLog.query.count()
        print(f"Verification: ReportLog table access successful (Row count: {count}).")
    except Exception as e:
        print(f"Verification Failed: {e}")
