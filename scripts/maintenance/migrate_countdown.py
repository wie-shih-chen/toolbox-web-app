import sqlite3
import os
import sys

# 確保可以載入 app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import app, db
from models import Countdown

def migrate():
    """建立倒數日與紀念日資料表"""
    with app.app_context():
        # 建立所有尚未存在的表 (包含新加的 Countdown)
        db.create_all()
        print("✅ 成功建立 Countdown 資料表！")

if __name__ == '__main__':
    migrate()
