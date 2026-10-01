# 使用輕量級的 Python 3.10 官方映像檔
FROM python:3.10-slim

# 設定環境變數
ENV PYTHONUNBUFFERED=True \
    PORT=8080

# 宣告工作目錄
WORKDIR /app

# 1. 安裝系統級相依軟體 (LibreOffice 與中文字體)
# 更新套件清單並安裝 LibreOffice 核心與中文字體，避免轉檔時中文變成亂碼
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice \
    libreoffice-writer \
    libreoffice-impress \
    libreoffice-calc \
    fonts-wqy-zenhei \
    fonts-wqy-microhei \
    fonts-noto-cjk \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 2. 複製 Python 套件清單並安裝
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. 複製專案的所有程式碼到容器內
COPY . .

# 4. 啟動伺服器 (使用 gunicorn，這是雲端環境跑 Flask 的標準做法)
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app
