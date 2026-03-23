# 📊 工具箱 Web App - 完整架構總覽

這份文件整合了所有專案架構資訊，包含檔案結構、頁面結構、資料模型與 API 設計。

---

## 📂 Part 1: 專案檔案結構 (Project File Structure)

完整的檔案與資料夾配置圖：

```
web_app/
│
├── 🚀 核心啟動檔案
│   ├── app.py                      # Flask 應用主程式 (Entry Point)
│   ├── wsgi.py                     # WSGI 入口 (Production)
│   ├── config.py                   # 設定檔 (DB, Secret Key, Scheduler...)
│   ├── models.py                   # 資料庫模型 (User, Expense, Salary, Reminder...)
│   ├── extensions.py               # Flask 擴充套件初始化 (db, login_manager, mail...)
│   ├── requirements.txt            # Python 依賴套件
│   ├── Procfile                    # 部署設定檔 (Heroku/PythonAnywhere)
│   ├── .env                        # 環境變數 (🔒 勿上傳 Git)
│   └── app.db                      # SQLite 資料庫檔案
│
├── 🚦 routes/ (路由層 - HTTP 請求處理)
│   ├── auth.py                     # 認證相關 (登入/註冊/個人設定頁)
│   ├── main_routes.py              # 首頁與通用路由
│   ├── expense_routes.py           # 💰 記帳模組路由
│   ├── salary_routes.py            # 💼 薪資模組路由
│   ├── ntut_routes.py              # 🏫 整合行事曆路由 (多來源 ICS 管理 API)
│   ├── reminder_routes.py          # 🔔 提醒事項路由
│   ├── download_routes.py          # 📥 影音下載器路由
│   ├── line_routes.py              # 📱 LINE Bot Webhook
│   └── settings_api.py             # ⚙️ 設定專用 API (AJAX)
│
├── 🧠 services/ (服務層 - 商業邏輯處理)
│   ├── data_service.py             # 通用資料處理
│   ├── expense_service.py          # 記帳邏輯 (CRUD, 統計, 週期計算)
│   ├── salary_service.py           # 薪資計算與排班邏輯 (自動偵測國定假日工資加倍)
│   ├── tw_holidays.py              # 國定假日服務 (Google ICS 圖 + 勞基法白名單過濾)
│   ├── reminder_service.py         # 提醒排程與通知發送
│   ├── calendar_notify_service.py  # 🗋 行事曆 ICS 每日前一天通知 (APScheduler)
│   ├── report_service.py           # 報表生成 (Excel, PDF)
│   ├── email_service.py            # Email 發送邏輯
│   └── line_service.py             # LINE 訊息推送邏輯
│
├── 🎨 templates/ (前端頁面 - Jinja2 模板)
│   ├── base.html                   # 🏗️ 基礎版型 (Header, Nav, Footer)
│   ├── index.html                  # 🏠 首頁
│   ├── manual.html                 # 📖 使用手冊
│   │
│   ├── auth/                       # 🔐 認證模組
│   │   ├── login.html
│   │   ├── register.html
│   │   ├── forgot_password.html
│   │   ├── reset_password.html
│   │   └── settings.html           # ⚙️ 帳號總設定 (個人資料/通知偏好)
│   │
│   ├── expense/                    # 💰 記帳模組
│   │   ├── today.html              # 本日記帳
│   │   ├── dashboard.html          # 本週期儀表板
│   │   ├── history.html            # 歷史記帳查詢
│   │   └── settings.html           # ⚙️ 記帳設定 (預算/類別/固定支出)
│   │
│   ├── salary/                     # 💼 薪資模組
│   │   ├── dashboard.html          # 本週排班
│   │   ├── monthly.html            # 月曆檢視 (國定假日標記 + 手機7欄等寬網格)
│   │   ├── history.html            # 歷史排班 (此週期匯出 + 匯出全部)
│   │   └── settings.html           # ⚙️ 薪資設定 (時薪/勞健保)
│   │
│   ├── reminders/                  # 🔔 提醒事項模組
│   │   └── index.html              # 提醒列表與設定
│   │
│   ├── ntut/                       # 🏫 整合行事曆模組
│   │   └── calendar.html           # 行事曆 (FullCalendar 多來源 ICS)
│   │
│   └── email/                      # 📧 Email 模板
│       ├── welcome.html
│       ├── reset_password.html
│       ├── expense_export.html
│       ├── salary_export.html
│       └── test_notification.html
│
├── 🎨 static/ (靜態資源)
│   ├── css/                        # 樣式表
│   │   ├── style.css               # 全域樣式
│   │   ├── expense.css             # 記帳專用樣式
│   │   ├── salary.css              # 薪資專用樣式
│   │   └── downloader.css          # 下載器專用樣式
│   │
│   ├── js/                         # JavaScript 腳本
│   │   ├── main.js                 # 全域功能 (Toast, Modal...)
│   │   ├── expense.js              # 記帳互動邏輯
│   │   ├── salary.js               # 薪資互動邏輯
│   │   ├── settings_autosave.js    # 設定自動儲存
│   │   ├── avatar_cropper.js       # 頭像裁切
│   │   └── avatar_preview.js       # 頭像預覽
│   │
│   └── img/                        # 圖片資源
│       └── line_qr_code.png        # LINE Bot QR Code
│
├── 🛠️ scripts/ (維護腳本)
│   └── maintenance/                     # 手動執行的一次性遷移腳本（已加中文註解）
│       ├── init_db.py                   # 全新展開時建立所有資料表
│       ├── migrate_settings_v1.py       # 新增時薪/預算警戒等基礎欄位
│       ├── migrate_settings_v2.py       # 新增帳単週期/自訂類別/固定支出
│       ├── migrate_settings_v3.py       # 新增 quick_shortcuts 欄位
│       ├── migrate_settings_v4.py       # 新增 monthly_report_day 欄位
│       ├── migrate_avatar_v6.py         # 新增 avatar_type / avatar_val 欄位
│       ├── migrate_line_bot_v5.py       # 新增 LINE Bot 綁定相關欄位
│       ├── migrate_calendar_notify_log.py # 建立 CalendarNotificationLog 資料表
│       ├── migrate_calendar_settings.py  # 新增行事曆通知設定欄位
│       └── migrate_holiday_pay.py        # 补算舊排班國定假日工資加倍 (--apply 實際寫入)
│
└── 📦 其他資料檔案
    ├── expense_data.json           # 舊版記帳資料 (已遷移至 DB)
    ├── salary_data.json            # 舊版薪資資料 (已遷移至 DB)
    └── downloads/                  # 暫存下載檔案
```

---

## 🗺️ Part 2: 功能頁面結構 (Page Structure)

使用者可訪問的頁面與功能導覽：

```
🏠 首頁 (/)
│
├── 💼 薪水小幫手 (/salary)
│   ├── 本週排班 (dashboard)  — 已移除匯出按鈕
│   ├── 月曆檢視 (monthly) — 紅色國定假日標籤 + 排班顯示 ×2 + CSS Grid 7欄等寬(手機對齊)
│   ├── 歷史排班 (history) — 含備註欄（國定假日工資加倍說明）
│   │   ├── 📅 此週期匯出（只匯出目前選取月份週期）
│   │   └── 📤 匯出全部（所有歷史資料）
│   └── ⚙️ 設定 (settings)
│       ├── 時薪設定
│       ├── 勞保/健保扣款
│       └── 通知偏好
│
├── 💰 記帳工具 (/expense)
│   ├── 本日記帳 (today)
│   ├── 本週期儀表板 (dashboard/index)
│   ├── 歷史記帳 (history)
│   │   └── 可依年份 → 月份查詢，點擊每筆資料彈出編輯視窗
│   └── ⚙️ 設定 (settings)
│       ├── 每期預算上限
│       ├── 預算警戒水位
│       ├── 資料可編輯範圍
│       ├── 帳單週期起始日
│       ├── 自訂類別 (emoji + 名稱 + 顏色)
│       ├── 固定支出 (名稱、金額、日期、類別)
│       └── 快捷摘要 (emoji + 名稱)
│
├── 📅 整合行事曆 (/ntut/calendar)
│   ├── 多來源日曆管理 (側邊欄顯示清單)
│   ├── 支援訂閱 ICS URL (如北科大/台科大校曆)
│   ├── 支援上傳本地 .ics 實體檔案
│   ├── 內建 FullCalendar 呈現 (自訂標籤顏色、點擊行程彈出詳細視窗)
│   ├── 每個日曆小鈴鐺圖示 (🔔 即時靜音切換)
│   └── ⚙️ 通知設定 (/ntut/calendar/settings)
│       ├── 開啟/關閉行事曆通知 (Toggle)
│       ├── 自訂傳送時間 (預設 20:00)
│       ├── 顯示總設定通知方式 (LINE / Email 彩色標籤)
│       └── 個別日曆靜音開關
├── 🔔 提醒事項 (/reminders)
│   └── 提醒列表與設定 (index)
│       ├── 新增/編輯提醒
│       ├── 頻率設定 (單次/每天/每週/每月)
│       ├── 週間選擇器
│       └── 通知方式 (LINE/Email)
│
├── 📥 影音下載器 (/download)
│   └── YouTube 下載 (downloader)
│
└── ⚙️ 帳號設定 (/auth/settings)
    ├── 個人設定 (Profile)
    │   ├── 頭像上傳/裁切
    │   ├── 使用者名稱
    │   └── Email
    │
    ├── 📱 LINE 官方帳號設定
    │   ├── 綁定狀態查詢
    │   └── 驗證碼生成
    │
    ├── 🔔 通知方式偏好
    │   ├── Email 月報表
    │   ├── LINE 即時通知
    │   └── 檔案下載完成通知
    │
    └── 🗂️ 資料管理中心
        ├── 修改密碼
        ├── 全站資料備份 (Excel)
        └── ⚠️ 危險區域 (重置薪資/記帳模組)
```

---

## 🗄️ Part 3: 資料模型結構 (Database Models)

所有資料表與關聯設計：

```
📊 資料庫 (app.db - SQLite)
│
├── User (用戶主表)
│   ├── id (PK)
│   ├── username
│   ├── email
│   ├── password_hash
│   ├── avatar_path
│   └── created_at
│
├── UserSettings (用戶設定 - One-to-One with User)
│   ├── id (PK)
│   ├── user_id (FK → User)
│   │
│   ├── 📧 通知設定
│   │   ├── line_user_id
│   │   ├── binding_code, binding_expiry
│   │   ├── notification_methods (JSON Array)
│   │   ├── monthly_report_day (Integer)
│   │   ├── calendar_notify_enabled (行事曆通知開關, Boolean)
│   │   └── calendar_notify_time    (通知時間 HH:MM, 預設 20:00)
│   │
│   ├── 💰 記帳設定
│   │   ├── monthly_budget (Integer)
│   │   ├── budget_alert_threshold (Integer)
│   │   ├── editable_month_range (Integer)
│   │   ├── billing_cycle_start_day (Integer)
│   │   ├── custom_categories (JSON Text)
│   │   │   └── [{ name: "類別", emoji: "🏷️", color: "#a78bfa" }, ...]
│   │   ├── recurring_expenses (JSON Text)
│   │   │   └── [{ name: "項目", amount: 390, day: 5, category: "..." }, ...]
│   │   └── quick_shortcuts (JSON Text)
│   │       └── [{ name: "快捷名稱", emoji: "⚡" }, ...]
│   │
│   └── 💼 薪資設定
│       ├── hourly_rate (Decimal)
│       ├── labor_insurance (Decimal)
│       └── health_insurance (Decimal)
│
├── Expense (記帳記錄 - One-to-Many with User)
│   ├── id (PK)
│   ├── user_id (FK → User)
│   ├── date (Date)
│   ├── amount (Decimal)
│   ├── category (String)
│   ├── description (Text)
│   ├── period_id (String, 例: "2024-02")
│   └── created_at (DateTime)
│
├── Shift (排班記錄 - One-to-Many with User)
│   ├── id (PK)
│   ├── user_id (FK → User)
│   ├── date (Date)
│   ├── start_time (Time)
│   ├── end_time (Time)
│   ├── break_minutes (Integer)
│   ├── notes (Text)
│   └── created_at (DateTime)
│
├── SalaryPeriod (薪資週期 - One-to-Many with User)
│   ├── id (PK)
│   ├── user_id (FK → User)
│   ├── start_date (Date)
│   ├── end_date (Date)
│   ├── total_hours (Decimal)
│   ├── total_pay (Decimal)
│   └── created_at (DateTime)
│
├── UserCalendar (使用者 ICS 來源 - One-to-Many with User)
│   ├── id (PK)
│   ├── user_id (FK → User)
│   ├── name           # 日曆名稱
│   ├── source_type    # 'url' | 'file'
│   ├── source         # URL 或檔案路徑
│   ├── color          # 自訂顏色 (hex)
│   ├── notify_enabled # 是否發送通知 (Boolean, 預設 True)
│   └── created_at
│
└── CalendarNotificationLog (日曆通知發送記錄 - 防重複)
    ├── id (PK)
    ├── user_id (FK → User)
    ├── cal_id         # UserCalendar ID
    ├── event_key      # "{cal_id}:{start_date}:{title[:100]}"
    ├── sent_date      # 發送日期 (YYYY-MM-DD)
    └── created_at
```

---

## 🔌 Part 4: API 端點結構 (API Endpoints)

後端 API 設計與用途：

```
/auth/api/ (認證與設定相關 API)
├── POST /update_email                  # 更新 Email
├── POST /update_notifications          # 更新通知偏好
├── POST /update_custom_categories      # 更新自訂類別 ← 嚴格驗證物件結構
├── POST /update_recurring_expenses     # 更新固定支出 ← 嚴格驗證物件結構
├── POST /update_quick_shortcuts        # 更新快捷摘要 ← 嚴格驗證物件結構
├── POST /set_preset_avatar             # 設定預設頭像
└── POST /test_notification             # 測試通知發送

/expense/api/ (記帳模組 API)
├── GET  /settings                      # 讀取記帳設定
├── POST /settings                      # 更新記帳設定
├── GET  /expenses                      # 查詢記帳資料 (支援查詢參數)
├── POST /expenses                      # 新增記帳記錄
├── PUT  /expenses/<id>                 # 更新記帳記錄
├── DELETE /expenses/<id>               # 刪除記帳記錄
└── GET  /period                        # 獲取當前週期資訊

/salary/api/ (薪資模組 API)
├── GET  /records                       # 查詢排班資料
├── POST /records                       # 新增排班記錄 (國定假日自動 ×2)
├── PUT  /records/<id>                   # 更新排班記錄 (國定假日自動 ×2)
├── DELETE /records/<id>                 # 刪除排班記錄
├── GET  /api/holidays?year=YYYY        # 取得指定年度國定假日 JSON (從 Google ICS)
├── GET  /stats                         # 排班統計摘要
├── GET/POST /settings                  # 薪資設定
├── POST /actions/copy_week             # 複製上週排班
├── POST /actions/clear_week            # 清空本週排班
├── GET  /api/export                    # CSV 導出（全部資料）
├── GET  /api/export-period?period=YYYY-MM  # CSV 導出（單月週期，e.g. 2026-03）
├── GET  /api/history/periods           # 帳務週期清單 (依 billing_cycle_start_day 對齊)
├── GET  /api/history/data?start_date=&end_date=  # 指定區間歷史資料
└── GET  /api/income-trend              # 全歷史月收入趨勢圖資料

/reminders/api/ (提醒事項 API)
├── GET  /reminders                     # 查詢所有提醒
├── POST /reminders                     # 新增提醒
├── PUT  /reminders/<id>                # 更新提醒
├── DELETE /reminders/<id>              # 刪除提醒
└── POST /reminders/<id>/toggle         # 切換啟用/停用狀態

/ntut/ (行事曆 API)
├── GET  /calendar                      # 行事曆頁面
├── GET  /calendar/settings             # 通知設定頁面
├── GET  /calendar/settings/api         # 讀取通知設定 (JSON)
├── POST /calendar/settings/api         # 儲存通知設定
├── GET  /calendars                     # 列出日曆清單 (含 notify_enabled)
├── POST /calendars                     # 新增日曆 (URL 或 .ics 檔案)
├── PUT  /calendars/<id>                # 更新名稱/顏色/notify_enabled
├── DELETE /calendars/<id>              # 刪除日曆
└── GET  /calendars/<id>/events         # 取得 FullCalendar JSON 事件

/line/webhook (LINE Bot Webhook)
└── POST /webhook                       # LINE 平台事件接收

/download/api/ (下載器 API)
├── POST /download                      # 提交下載任務
└── GET  /status/<task_id>              # 查詢下載狀態
```

---

## 🛠️ 核心技術棧 (Tech Stack)

| 技術層       | 使用技術                          |
|--------------|-----------------------------------|
| **後端框架** | Flask 3.x                         |
| **資料庫**   | SQLite (本地), PostgreSQL (雲端可選) |
| **ORM**      | Flask-SQLAlchemy                  |
| **認證**     | Flask-Login                       |
| **排程**     | APScheduler                       |
| **Email**    | Flask-Mail                        |
| **前端**     | Jinja2, Bootstrap 5, Vanilla JS   |
| **部署**     | PythonAnywhere / Heroku           |

---

## 📌 重要提醒

### 1. 設定資料格式要求
所有設定資料必須符合**物件陣列格式**：
- `custom_categories`: `[{ name, emoji, color }, ...]`
- `recurring_expenses`: `[{ name, amount, day, category }, ...]`
- `quick_shortcuts`: `[{ name, emoji }, ...]`

### 2. 提醒功能注意事項
- APScheduler 每分鐘檢查一次提醒
- PythonAnywhere 免費版可能會休眠，建議定期喚醒或升級方案

### 3. 資料庫遷移
- 全新展開時執行 `scripts/maintenance/init_db.py` 建立所有資料表
- 需要資料庫結構升級時，執行 `scripts/maintenance/migrate_*.py` （每支腳本內部均有中文說明使用時機與方法）

---

## 📱 Part 5: 手機畫面設計要求 (Mobile Design Requirements)

### 5.1 響應式斷點 (Responsive Breakpoints)

```css
/* 平板 */
@media (max-width: 768px) {
    /* 適度縮小，保持多欄佈局 */
}

/* 手機橫向 / 小平板 */
@media (max-width: 600px) {
    /* 主要手機優化區間 */
    /* 兩欄網格或橫向緊湊佈局 */
}

/* 小手機 */
@media (max-width: 480px) {
    /* 進一步縮小字體和間距 */
}

/* 極小螢幕 */
@media (max-width: 400px) {
    /* 最小可用尺寸 */
}
```

---

### 5.2 觸控目標尺寸 (Touch Target Sizes)

所有可點擊元素必須符合以下尺寸標準：

| 元素類型 | 最小尺寸 | 建議尺寸 |
|----------|----------|----------|
| 按鈕 | 44px × 44px | 48px × 48px |
| 圖標按鈕 | 40px × 40px | 44px × 44px |
| 輸入框高度 | 40px | 44px |
| 列表項 | 48px | 56px |
| 關閉按鈕 | 36px × 36px | 40px × 40px |

**重要規則**：
- ✅ 使用 `min-height: 44px` 確保按鈕高度
- ✅ 增加 padding 而非縮小內容
- ✅ 確保間距至少 8px 避免誤觸

---

### 5.3 輸入框設計 (Input Field Design)

#### 防止 iOS 自動縮放
```css
input[type="text"],
input[type="number"],
textarea {
    font-size: 16px; /* 必須 ≥16px 防止 iOS 自動放大 */
}
```

#### 緊湊橫向佈局
```css
/* 600px 以下螢幕 */
.input-group {
    gap: 4px;              /* 最小間距 */
}

input[type="text"] {
    padding: 9px 10px;     /* 緊湊 padding */
}

/* Emoji 輸入框 */
input[id*="Emoji"] {
    width: 48px;           /* 固定小寬度 */
    padding: 9px 6px;
    font-size: 1rem;
}

/* 顏色選擇器 */
input[type="color"] {
    width: 45px;
    padding: 5px;
}

/* 按鈕 */
button {
    padding: 9px 12px;
    font-size: 0.88rem;
    /* 移除 min-width 讓按鈕自適應 */
}
```

**關鍵原則**：
- ❌ 避免輸入框 `width: 100%` 導致溢出
- ✅ 使用固定小寬度 + flex: 1 搭配
- ✅ 總寬度控制在螢幕範圍內

---

### 5.4 卡片網格佈局 (Card Grid Layout)

```css
/* 桌面：自適應多欄 */
.category-grid,
.shortcut-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
    gap: 12px;
}

/* 平板 */
@media (max-width: 768px) {
    .category-grid,
    .shortcut-grid {
        grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
        gap: 10px;
    }
}

/* 手機：兩欄 */
@media (max-width: 600px) {
    .category-grid,
    .shortcut-grid {
        grid-template-columns: 1fr 1fr;
        gap: 8px;
    }
}
```

**設計原則**：
- ✅ 手機使用兩欄網格（視覺平衡）
- ❌ 避免手機單欄（浪費空間）
- ✅ 卡片 `min-height` 防止過小

---

### 5.5 模態框設計 (Modal Dialog Design)

模態框必須在桌面和手機上都提供良好的體驗。

#### 桌面版（標準模態框）
```css
.expense-modal {
    position: fixed;
    z-index: 9999;
    left: 0;
    top: 0;
    width: 100%;
    height: 100%;
    display: none; /* 或 flex 當顯示時 */
    align-items: center;       /* 垂直居中 */
    justify-content: center;   /* 水平居中 */
    padding: 20px;
}

.expense-modal-content {
    max-width: 480px;          /* 限制最大寬度 */
    width: 100%;
    max-height: 90vh;          /* 最高 90% 視窗高度 */
    border-radius: 16px;
}
```

#### 手機版（底部彈出式 Bottom Sheet）
```css
@media (max-width: 600px) {
    .expense-modal {
        padding: 0;
        align-items: flex-end;    /* 底部對齊（底部彈出效果）*/
    }

    .expense-modal-content {
        max-width: 100%;
        width: 100%;
        max-height: 90vh;           /* 最高 90% 視窗高度 */
        border-radius: 24px 24px 0 0;  /* 僅頂部圓角（底部彈出式）*/
        display: flex;
        flex-direction: column;
        overflow: hidden;
        margin-bottom: 0;           /* 貼底部 */
        padding-bottom: calc(20px + env(safe-area-inset-bottom)); /* iOS 安全區域 */
    }

    /* 固定頭部 */
    .expense-modal-header {
        flex-shrink: 0;
    }

    /* 可滾動主體 */
    .expense-modal-body {
        flex: 1;
        overflow-y: auto;
        -webkit-overflow-scrolling: touch;
    }

    /* 固定底部 */
    .expense-modal-footer {
        flex-shrink: 0;
    }
}
```

**關鍵要求**：

**桌面版**：
- ✅ 居中顯示（`align-items: center`, `justify-content: center`）
- ✅ `max-width: 480px`（標準模態框寬度）
- ✅ `max-height: 90vh`（不超過視窗高度）
- ✅ 四周圓角 `border-radius: 16px`

**手機版（底部彈出式）**：
- ✅ 底部對齊（`align-items: flex-end`）
- ✅ `max-height: 90vh`（不佔滿螢幕）
- ✅ 僅頂部圓角 `border-radius: 24px 24px 0 0`
- ✅ iOS 安全區域支援（`env(safe-area-inset-bottom)`）

**JavaScript 操作**：
```javascript
// 開啟模態框 - 簡單切換 display
function openModal() {
    modal.style.display = 'flex';
}

// 關閉模態框
function closeModal() {
    modal.style.display = 'none';
}
```

> [!WARNING]
> **不要**使用 `document.body.style.position = 'fixed'` 來鎖定滾動！
> 這會導致頁面無法滾動。其他模態框都只是簡單地切換 display 屬性。

**通用要求**：
- ✅ Flex 佈局固定頭尾，可滾動主體
- ✅ 點擊遮罩關閉
- ✅ ESC 鍵關閉（可選）

---

### 5.6 拖動排序設計 (Drag and Drop)

```javascript
Sortable.create(element, {
    animation: 150,
    handle: '.drag-handle',  // 僅通過手柄拖動
    ghostClass: 'sortable-ghost'
});
```

**拖動手柄樣式**：
```css
.drag-handle {
    cursor: grab;
    opacity: 0.4;
    transition: opacity 0.2s;
}

.drag-handle:hover {
    opacity: 1;
}

/* 手機：較大的手柄 */
@media (max-width: 600px) {
    .drag-handle {
        font-size: 16px;
        margin-right: -2px;
    }
}
```

**原則**：
- ✅ 限制拖動區域為手柄圖標（⋮⋮）
- ❌ 避免整張卡片可拖動（誤觸）
- ✅ 手機上手柄稍大（16px）

---

### 5.7 字體縮放規則 (Font Scaling)

```css
/* 桌面 */
.category-emoji { font-size: 1.5rem; }
.category-name { font-size: 1rem; }

/* 平板 */
@media (max-width: 768px) {
    .category-emoji { font-size: 1.3rem; }
    .category-name { font-size: 0.9rem; }
}

/* 手機 */
@media (max-width: 480px) {
    .category-emoji { font-size: 1.2rem; }
    .category-name { font-size: 0.85rem; }
}
```

**縮放比例**：
- 大標題：1.25rem → 1.1rem → 1rem
- 正文：1rem → 0.9rem → 0.85rem
- 次要文字：0.9rem → 0.85rem → 0.8rem

---

### 5.8 常見問題與解決方案

| 問題 | 原因 | 解決方案 |
|------|------|----------|
| 輸入框超出螢幕 | inline style `width: 70px` 等固定寬度 | 使用 `max-width` 或 `!important` 覆蓋 |
| iOS 點擊輸入框自動放大 | `font-size < 16px` | 確保輸入框 `font-size: 16px` |
| 模態框需要向上滑才看到 | 頁面有滾動位置 | 開啟模態框時 `window.scrollTo(0, 0)` |
| 模態框太大佔滿螢幕 | `height: 100vh` | 改用 `max-height: 85vh` + padding |
| 拖動卡片誤觸 | 整張卡片可拖動 | 限制 `handle: '.drag-handle'` |
| 按鈕文字被截斷 | 寬度不足 | 移除 `min-width`，使用 `white-space: nowrap` |

---

### 5.9 測試清單 (Testing Checklist)

手機端發布前必須測試：

- [ ] **實際裝置測試**
  - [ ] iPhone Safari (iOS ≥15)
  - [ ] Android Chrome (Android ≥10)
  
- [ ] **輸入與表單**
  - [ ] 所有輸入框無需縮放即可看清
  - [ ] 點擊輸入框不會自動放大（iOS）
  - [ ] 所有按鈕可輕鬆點擊（≥44px）
  
- [ ] **佈局與滾動**
  - [ ] 無橫向滾動條
  - [ ] 模態框出現在視窗頂部（無需向上滑）
  - [ ] 模態框開啟時背景無法滾動
  
- [ ] **觸控互動**
  - [ ] 拖動手柄可正常拖動
  - [ ] 點擊卡片內容不會觸發拖動
  - [ ] 所有圖標按鈕間距足夠（防誤觸）
  
- [ ] **視覺與動畫**
  - [ ] 字體大小適中（無需放大閱讀）
  - [ ] 卡片間距合理
  - [ ] 動畫流暢（60fps）

---

**文件最後更新**: 2026-03-24  
**專案版本**: v2.4

### v2.4 更新摘要 (2026-03-24)

#### 薪水小幫手
- **匯出按鈕重整**：本週排班頁移除匯出按鈕；歷史排班改為兩個並排按鈕「📅 此週期匯出」與「📤 匯出全部」
- **新增 `/salary/api/export-period?period=YYYY-MM` 端點**：只匯出指定月份週期 CSV，同樣支援 Email/LINE/Download
- **修正帳務週期計算 (`get_monthly_periods`)**：原先產生日曆月週期 (1日~月底)，現根據 `billing_cycle_start_day` 產生正確週期（例：設10 → `02/10 ~ 03/09`）
- **修正月曆手機版格子對齊**：`monthly.html` 改用 CSS Grid `repeat(7, 1fr)`，解決手機上格子大小不一、無法與星期標題對齊的問題

#### 記帳工具
- **修正帳務週期末日被排除的 Bug**：`expense_service.py` `get_summary()` 過濾改用 `<=`（含），確保週期最後一天（如 3/9）資料正確歸入當期

#### 腳本整理
- 所有遷移腳本移至 `scripts/maintenance/` 並加入中文說明
- `migrate_settings.py` 重命名為 `migrate_settings_v1.py`

---

### v2.3 更新摘要 (2026-03)
- 新增整合行事曆功能：支援訂閱 ICS URL 與上傳本地 .ics 檔案
- 新增 `UserCalendar` 與 `CalendarNotificationLog` 資料模型
- 新增 `CalendarNotifyService` ：每日按用戶自訂時間掃描 ICS 日曆，发送「明天 XXX 」提醒
- 新增行事曆通知設定頁：開關、傳送時間、個別日曆靈音
- `UserSettings` 新增 `calendar_notify_enabled` 、`calendar_notify_time` 欄位
- `UserCalendar` 新增 `notify_enabled` 欄位（個別靈音）
- 豚子尋頂新增靈音可切換的 🔔 圖示按鈕
- 自導航布局 (base.html) 日曆點遠 「北科」 改名為 「日曆」

