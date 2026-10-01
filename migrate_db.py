import os
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker

def migrate(sqlite_url, postgres_url):
    print("🚀 開始準備資料庫搬家...")
    
    # 建立兩個資料庫的連線
    sqlite_engine = create_engine(sqlite_url)
    postgres_engine = create_engine(postgres_url)
    
    # 讀取 SQLite 的資料表結構
    meta = MetaData()
    meta.reflect(bind=sqlite_engine)
    
    # 建立 Postgres 的資料表
    print("📦 正在雲端建立資料表結構...")
    meta.create_all(bind=postgres_engine)
    
    # 開始搬運每個資料表的資料
    sqlite_session = sessionmaker(bind=sqlite_engine)()
    postgres_session = sessionmaker(bind=postgres_engine)()
    
    from sqlalchemy import text
    # 關閉 Postgres 的外鍵檢查（避免搬運順序報錯）
    postgres_session.execute(text("SET session_replication_role = 'replica';"))
    
    for table in meta.sorted_tables:
        print(f"📥 正在搬運表格: {table.name} ...")
        # 清空目標表格（避免重複）
        postgres_session.execute(table.delete())
        
        # 從 SQLite 讀取所有資料
        records = sqlite_session.execute(table.select()).fetchall()
        
        if records:
            # 轉換為字典格式並寫入 Postgres
            data = [dict(zip(table.columns.keys(), record)) for record in records]
            postgres_session.execute(table.insert(), data)
            print(f"   ✅ 成功搬運 {len(records)} 筆資料！")
        else:
            print(f"   - 表格為空，跳過。")
            
    # 恢復外鍵檢查並儲存
    postgres_session.execute(text("SET session_replication_role = 'origin';"))
    postgres_session.commit()
    print("🎉 資料搬家大成功！舊資料已經全部上傳到 Neon 雲端了！")

if __name__ == "__main__":
    neon_url = input("👉 請貼上你的 Neon Connection String (含密碼的完整網址): \n")
    if not neon_url.startswith("postgres"):
        print("❌ 錯誤：這看起來不像正確的資料庫網址喔！")
    else:
        # 修復 SQLAlchemy 不支援 postgres:// 的問題
        if neon_url.startswith("postgres://"):
            neon_url = neon_url.replace("postgres://", "postgresql://", 1)
            
        base_dir = os.path.dirname(os.path.abspath(__file__))
        sqlite_url = 'sqlite:///' + os.path.join(base_dir, 'app.db')
        
        try:
            migrate(sqlite_url, neon_url)
        except Exception as e:
            print(f"❌ 搬運失敗：{e}")
