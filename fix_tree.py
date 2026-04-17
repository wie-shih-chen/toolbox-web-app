import re

content = open('ARCHITECTURE.md', 'rb').read().decode('utf-8', errors='replace')

tree_start = content.find('## 📂 Part 2')
if tree_start == -1:
    tree_start = content.find('web_app/')

tree_end = content.find('## 🔒 Part 6:')
if tree_end == -1:
    tree_end = content.find('## 📱 Part 3') # or whatever is next

if tree_end == -1:
    print("Could not find end of tree string.")

old_tree = content[tree_start:tree_end]

new_tree = """## 📂 Part 2: 專案檔案結構 (File Structure & Modules)

```text
web_app/
│
├── 🚀 核心啟動檔案
│   ├── app.py                      # Flask 應用主程式 (Entry Point)，負責載入配置與啟動伺服器
│   ├── wsgi.py                     # WSGI 入口 (Production)，供 Gunicorn 等生產環境伺服器呼叫
│   ├── config.py                   # 系統全域設定檔 (包含 DB / Secret Key / Scheduler / Mail 等參數)
│   ├── models.py                   # 資料庫 ORM 模型 (定義 User, Expense, Salary, Reminder 等綱要)
│   ├── extensions.py               # Flask 擴充套件初始化中心 (db, login_manager, mail, bcrypt)
│   ├── requirements.txt            # Python 依賴套件清單，用於 pip install -r
│   ├── Procfile                    # 雲端部署設定檔 (支援 Heroku / PythonAnywhere 啟動指令)
│   ├── .env                        # 系統環境變數 (🔒 存放敏感情資，勿上傳 Git)
│   └── app.db                      # SQLite 實體資料庫檔案 (Local 開發用)
│
├── 🚦 routes/ (路由層 - HTTP 請求處理)
│   ├── auth.py                     # 密碼學與認證模組 (登入 / 註冊 / 忘記密碼 / 個人設定頁面 rendering)
│   ├── main_routes.py              # 系統核心路由 (首頁儀表板 / 使用手冊 / 導覽列通用邏輯)
│   ├── expense_routes.py           # 💰 記帳模組路由 (CRUD API 與頁面呈現)
│   ├── salary_routes.py            # 💼 薪資模組路由 (排班管理 / CSV匯出 / 月曆顯示)
│   ├── period_routes.py            # 🩸 生理期追蹤路由 (經期紀錄 API 與月曆呈現)
│   ├── countdown_routes.py         # ⏳ 倒數與紀念日路由 (獨立卡片 / 圖片自動裁切 API / 目標計算)
│   ├── ntut_routes.py              # 🏫 整合行事曆路由 (北科大 ICS 解析 / 多來源 ICS 訂閱管理 API)
│   ├── reminder_routes.py          # 🔔 提醒事項路由 (單次與週期性提醒建立 API)
│   ├── download_routes.py          # 📥 影音下載器路由 (對接 yt-dlp 任務處理)
│   ├── line_routes.py              # 📱 LINE Bot Webhook (處理 LINE Server 推播事件與互動)
│   └── settings_api.py             # ⚙️ 設定專用 API (非同步 AJAX 儲存個人偏好與自動儲存)
│
├── 🧠 services/ (服務層 - 商業邏輯處理)
│   ├── data_service.py             # 通用資料處理與工具函數庫 (日期轉換、文字過濾)
│   ├── expense_service.py          # 記帳深度邏輯 (資料聚合、統計圖表計算、跨期帳務處理)
│   ├── salary_service.py           # 薪資邏輯分析 (時數精算 / 自動偵測國定假日 / 工資加倍計算)
│   ├── countdown_service.py        # ⏳ 倒數邏輯演算 (未來天數反向推算、Base64 圖片編碼與壓縮儲存)
│   ├── period_service.py           # 🩸 生理期醫學標準算法 (動態加權平均週期計算 / 易孕期與排卵日推算)
│   ├── tw_holidays.py              # 國定假日判定服務 (整合 Google Calendar ICS + 勞基法白名單過濾)
│   ├── reminder_service.py         # 提醒排程排隊與通知實際派發邏輯
│   ├── calendar_notify_service.py  # 🗋 行事曆自動化服務 (每日自動掃描 ICS 並透過 APScheduler 發送前一天通知)
│   ├── report_service.py           # 報表生成引擎 (Excel / PDF / CSV 高效生成與格式化)
│   ├── email_service.py            # Email 遞送邏輯 (SMTP 整合與 HTML 模板渲染)
│   ├── line_service.py             # LINE 訊息互動邏輯 (推播 Flex Message 卡片與文字)
│   └── period_notify_service.py    # 🩸 生理期預測通知服務 (透過 APScheduler 每日檢查並提前提醒)
│
├── 🎨 templates/ (前端頁面 - Jinja2 模板)
│   ├── base.html                   # 🏗️ 基礎版型底圖 (包含全局 Header, 側邊/底部 Nav, Modal 框架全域載入)
│   ├── index.html                  # 🏠 首頁儀表板 (整合各模組 Widget 捷徑區塊)
│   ├── manual.html                 # 📖 使用教學手冊 (靜態說明文檔)
│   │
│   ├── auth/                       # 🔐 認證與帳戶中心
│   │   ├── login.html              # 登入介面
│   │   ├── register.html           # 帳戶註冊介面
│   │   ├── forgot_password.html    # 忘記密碼發信介面
│   │   ├── reset_password.html     # 密碼重置操作介面
│   │   └── settings.html           # ⚙️ 帳號全局設定 (個人資料維護 / 總通知偏好切換)
│   │
│   ├── expense/                    # 💰 記帳管理模組
│   │   ├── today.html              # 本日快速記帳介面
│   │   ├── dashboard.html          # 本週期智慧儀表板 (預算圓餅圖與趨勢圖表)
│   │   ├── history.html            # 歷史記帳深度查詢與過濾清單
│   │   └── settings.html           # ⚙️ 記帳專屬設定 (動態預算 / 自訂分類 / 綁定固定支出)
│   │
│   ├── salary/                     # 💼 薪資小幫手模組
│   │   ├── dashboard.html          # 本週排班表與本期薪資試算
│   │   ├── monthly.html            # 月曆檢視模式 (7欄等寬 RWD，支援國定假日標記)
│   │   ├── history.html            # 歷史排班紀錄 (支援此週期單獨匯出與全部結算匯出)
│   │   └── settings.html           # ⚙️ 薪資獨立設定 (基礎時薪 / 勞健保扣除額)
│   │
│   ├── period/                     # 🩸 生理期追蹤模組
│   │   ├── dashboard.html          # 週期狀態儀表板 (支援狀態橫幅與 FullCalendar 視覺化預測月曆)
│   │   └── settings.html           # ⚙️ 生理期追蹤設定 (歷史紀錄管理 / 自動防抖儲存)
│   │
│   ├── reminders/                  # 🔔 提醒事項中心
│   │   └── index.html              # 提醒項目列表與快速開關介面
│   │
│   ├── countdown/                  # ⏳ 倒數日與里程碑模組
│   │   ├── index.html              # 倒數主清單 (Glassmorphism 璃光卡片顯示)
│   │   └── detail.html             # 獨立倒數事件詳情 (顯示時間軸、下一個目標推算與快速編輯)
│   │
│   ├── ntut/                       # 🏫 整合行事曆模組
│   │   ├── calendar.html           # 多來源行事曆主介面 (整合 FullCalendar 與假日資料)
│   │   └── settings.html           # ⚙️ 行事曆通知與來源設定 (ICS 訂閱管理)
│   │
│   └── email/                      # 📧 系統 Email 版型
│       ├── welcome.html            # 註冊歡迎信模板
│       ├── reset_password.html     # 忘記密碼恢復信模板
│       ├── expense_export.html     # 記帳記錄匯出信件模板
│       ├── salary_export.html      # 排班記錄匯出信件模板
│       └── test_notification.html  # 系統通知測試信模板
│
└── 🎨 static/ (靜態資源 - CSS / JS / 圖片)
    ├── css/                        # 樣式表 (CSS)
    │   ├── style.css               # 全域核心樣式 (Root Variables / 共用元件 / RWD 框架)
    │   ├── expense.css             # 記帳模組專屬樣式 (圖表容器 / 收支卡片樣式)
    │   ├── expense-modal.css       # 記帳快速彈出視窗獨立樣式 (優化 Z-index 與動畫)
    │   ├── salary.css              # 薪資模組專屬樣式 (班表清單 / 月曆網格)
    │   └── downloader.css          # 📥 下載器模組專屬樣式
    │
    ├── js/                         # JavaScript 邏輯控制
    │   ├── main.js                 # 全局核心邏輯 (導航互動 / AJAX CSRF / 共用 Alert)
    │   ├── expense.js              # 記帳模組前端互動 (Chart.js 初始化 / 動態表單計算)
    │   ├── salary.js               # 排班模組前端互動 (日期檢驗 / 快速快選時間)
    │   ├── avatar_cropper.js       # 圖片裁切核心引擎 (整合 Cropper.js 處理倒數卡片圖片)
    │   ├── avatar_preview.js       # 圖片即時預覽與 FileReader 解析
    │   └── settings_autosave.js    # 全域設定防抖自動儲存引擎 (Auto-Save 機制)
    │
    └── img/                        # 系統靜態圖片與圖標
        └── line_qr_code.png        # LINE Bot 快速綁定 QR Code 資源
```

"""

new_content = content[:tree_start] + new_tree + content[tree_end:]

with open('ARCHITECTURE.md', 'wb') as f:
    f.write(new_content.encode('utf-8'))
print("Successfully replaced tree structure.")
