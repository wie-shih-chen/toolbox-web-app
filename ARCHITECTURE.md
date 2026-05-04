# 📊 工具箱 Web App - 完整架構總覽

> **最後更新**：2026-05-04 | **版本**：v3.1（多帳號通知精準分流 + 智慧匯出與報表優化）  
> 這份文件整合了所有專案架構資訊，閱讀順序建議：Part 1 → Part 2 → Part 3 → Part 4

---

## 📂 Part 1: 專案檔案結構 (File Structure)

```text
web_app/
│
├── 🚀 核心啟動檔案
│   ├── app.py                      # Flask 應用主程式，負責載入配置 & 啟動伺服器
│   ├── wsgi.py                     # WSGI 入口 (Production)，供 Gunicorn 等生產伺服器呼叫
│   ├── config.py                   # 系統全域設定檔 (DB / Secret Key / Scheduler / Mail 等)
│   ├── models.py                   # 資料庫 ORM 模型 (所有資料表定義)
│   ├── extensions.py               # Flask 擴充套件初始化中心 (db, login_manager, mail)
│   ├── requirements.txt            # Python 依賴套件清單
│   ├── Procfile                    # 雲端部署設定 (PythonAnywhere / Heroku)
│   ├── .env                        # 🔒 環境變數 (SECRET_KEY, LINE Token 等，勿上傳 Git)
│   └── app.db                      # SQLite 實體資料庫 (Local 開發用)
│
├── 🚦 routes/ (路由層 - HTTP 請求處理)
│   ├── auth.py                     # 認證 & 帳戶 (登入/註冊/設定/LINE 多帳號綁定 API)
│   ├── main_routes.py              # 首頁儀表板 / 使用手冊
│   ├── expense_routes.py           # 💰 記帳模組 (CRUD API & 頁面)
│   ├── salary_routes.py            # 💼 薪資模組 (排班管理 / CSV匯出 / 月曆)
│   ├── period_routes.py            # 🩸 生理期追蹤 (紀錄 API & 月曆)
│   ├── countdown_routes.py         # ⏳ 倒數 & 紀念日 (卡片 / 圖片裁切 / 里程碑)
│   ├── ntut_routes.py              # 📅 整合行事曆 (ICS 解析 / 多來源訂閱管理)
│   ├── reminder_routes.py          # 🔔 提醒事項 (單次 & 週期性提醒)
│   ├── download_routes.py          # 📥 影音下載器 (yt-dlp 任務)
│   ├── line_routes.py              # 📱 LINE Bot Webhook (智慧語意解析 & 推播)
│   └── settings_api.py             # ⚙️ 設定專用 API (AJAX 非同步儲存)
│
├── 🧠 services/ (服務層 - 商業邏輯)
│   ├── data_service.py             # 通用工具函數 (日期轉換、文字過濾)
│   ├── expense_service.py          # 記帳深度邏輯 (聚合統計 / 圖表計算 / 跨期帳務)
│   ├── salary_service.py           # 薪資邏輯 (時數精算 / 國定假日偵測 / 工資加倍)
│   ├── countdown_service.py        # 倒數邏輯 (天數推算 / Base64 圖片壓縮)
│   ├── period_service.py           # 🩸 生理期算法 (加權平均週期 / 易孕期 / 排卵日推算)
│   ├── tw_holidays.py              # 國定假日判定 (Google Calendar ICS + 勞基法白名單)
│   ├── reminder_service.py         # 提醒排程 & 通知派發
│   ├── calendar_notify_service.py  # 📅 行事曆自動通知 (APScheduler 每日掃描 ICS)
│   ├── report_service.py           # 報表生成 (Excel / CSV 格式化輸出)
│   ├── email_service.py            # Email 遞送 (SMTP + HTML 模板渲染)
│   ├── line_service.py             # LINE 訊息互動 (推播 Flex Message & 純文字)
│   └── period_notify_service.py    # 🩸 生理期預測通知 (APScheduler 每日檢查 & 提前提醒)
│
├── 🎨 templates/ (前端頁面 - Jinja2)
│   ├── base.html                   # 基礎版型 (全局 Header / 底部/側邊 Nav / Modal 框架)
│   ├── index.html                  # 首頁儀表板 (各模組 Widget 捷徑)
│   ├── manual.html                 # 使用說明手冊
│   │
│   ├── auth/
│   │   ├── login.html              # 登入介面
│   │   ├── register.html           # 帳戶註冊
│   │   ├── forgot_password.html    # 忘記密碼
│   │   ├── reset_password.html     # 密碼重置
│   │   └── settings.html           # ⚙️ 帳號設定 (個人資料 / LINE 多帳號管理 / 通知偏好)
│   │
│   ├── expense/
│   │   ├── today.html              # 當日快速記帳
│   │   ├── dashboard.html          # 週期智慧儀表板 (預算圓餅圖 & 趨勢圖)
│   │   ├── history.html            # 歷史查詢 & 過濾清單
│   │   └── settings.html           # ⚙️ 記帳設定 (預算 / 自訂分類 / 固定支出)
│   │
│   ├── salary/
│   │   ├── dashboard.html          # 本週排班 & 薪資試算
│   │   ├── monthly.html            # 月曆模式 (7欄等寬 RWD，國定假日標記)
│   │   ├── history.html            # 歷史排班紀錄 & 匯出
│   │   └── settings.html           # ⚙️ 薪資設定 (基礎時薪 / 扣除額)
│   │
│   ├── period/
│   │   ├── dashboard.html          # 週期儀表板 (狀態橫幅 & FullCalendar 視覺化)
│   │   └── settings.html           # ⚙️ 生理期設定 (歷史紀錄管理 / 自動儲存)
│   │
│   ├── reminders/
│   │   └── index.html              # 提醒清單 & 快速開關
│   │
│   ├── countdown/
│   │   ├── index.html              # 倒數主清單 (Glassmorphism 卡片)
│   │   └── detail.html             # 倒數事件詳情 (時間軸 / 目標推算 / 快速編輯)
│   │
│   ├── ntut/
│   │   ├── calendar.html           # 多來源行事曆 (FullCalendar & 假日整合)
│   │   └── settings.html           # ⚙️ 行事曆通知 & 來源設定
│   │
│   └── email/
│       ├── welcome.html            # 歡迎信
│       ├── reset_password.html     # 密碼重置信
│       ├── expense_export.html     # 記帳匯出信
│       ├── salary_export.html      # 排班匯出信
│       └── test_notification.html  # 通知測試信
│
├── 🎨 static/ (靜態資源)
│   ├── css/
│   │   ├── style.css               # 全域核心樣式 (CSS 變數 / 共用元件 / RWD)
│   │   ├── expense.css             # 記帳模組樣式
│   │   ├── expense-modal.css       # 記帳快速彈出視窗樣式
│   │   ├── salary.css              # 薪資模組樣式
│   │   └── downloader.css          # 下載器樣式
│   │
│   ├── js/
│   │   ├── main.js                 # 全局核心邏輯 (導航 / AJAX CSRF / Alert)
│   │   ├── expense.js              # 記帳前端互動 (Chart.js / 動態表單)
│   │   ├── salary.js               # 排班前端互動 (日期驗證 / 快選時間)
│   │   ├── avatar_cropper.js       # 圖片裁切引擎 (整合 Cropper.js)
│   │   ├── avatar_preview.js       # 圖片即時預覽 & FileReader
│   │   └── settings_autosave.js    # 設定防抖自動儲存引擎
│   │
│   └── img/
│       └── line_qr_code.png        # LINE Bot 快速綁定 QR Code
│
└── 🔧 scripts/maintenance/ (維護腳本)
    ├── init_db.py                  # ⭐ 初始化所有資料表 (首次部署必跑)
    ├── migrate_line_bindings.py    # v3.0 遷移：UserSettings.line_user_id → LineBinding
    ├── migrate_period_notify_types.py
    ├── migrate_settings_v1~v4.py   # 歷代設定欄位遷移
    └── migrate_*.py                # 其他各版本 DB 結構升級腳本
```

---

## 🗃️ Part 2: 資料庫模型 (Database Models)

### 2.1 User（使用者）
| 欄位 | 型態 | 說明 |
|------|------|------|
| `id` | Integer PK | |
| `username` | String(80) | 唯一帳號 |
| `email` | String(120) | 信箱（可選） |
| `password_hash` | String(120) | Scrypt/PBKDF2-SHA256 雜湊 |
| `avatar_type` | String(20) | `'preset'` 或 `'upload'` |
| `avatar_val` | String(255) | 預設名稱或上傳路徑 |

**Relationships**：`salary_records`, `expense_records`, `period_records`, `settings`, `reminders`, `line_bindings`

---

### 2.2 LineBinding（LINE 多帳號綁定）⭐ v3.0 新增
| 欄位 | 型態 | 說明 |
|------|------|------|
| `id` | Integer PK | |
| `user_id` | FK → User | 歸屬的網站帳號 |
| `line_user_id` | String(255) UNIQUE | LINE 的 Uid |
| `nickname` | String(50) | 自訂暱稱（如「本人」「女友」）|
| `permissions` | Text (JSON) | 允許的功能，例如 `["expense","salary","period"]` |
| `created_at` | DateTime | 建立時間 |

> **Permission keys**：`expense`（記帳）、`salary`（排班/獎金）、`period`（月經）

---

### 2.3 UserSettings（使用者設定）
| 欄位 | 型態 | 說明 |
|------|------|------|
| `user_id` | FK → User | |
| `hourly_rate` | Float | 時薪（預設 183） |
| `monthly_budget` | Float | 月預算（預設 10000） |
| `billing_cycle_start_day` | Integer | 帳單週期起始日（預設 10） |
| `custom_categories` | Text (JSON) | 自訂記帳分類清單 |
| `recurring_expenses` | Text (JSON) | 固定支出清單 |
| `quick_shortcuts` | Text (JSON) | 快速捷徑清單 |
| `line_user_id` | String(255) | ⚠️ 舊欄位（v3.0後改用 `LineBinding`，保留向下相容） |
| `binding_code` | String(6) | 6位驗證碼（新增 LineBinding 用） |
| `binding_expiry` | DateTime | 驗證碼過期時間（UTC，5分鐘有效） |
| `notification_methods` | Text (JSON) | `["email", "line"]` |
| `calendar_notify_enabled` | Boolean | 行事曆每日通知 |
| `calendar_notify_time` | String(5) | 通知時間 HH:MM |
| `period_notify_enabled` | Boolean | 生理期提前通知 |
| `period_notify_time` | String(5) | 通知時間（預設 08:00） |
| `period_notify_days_before` | Integer | 提早幾天通知（預設 3） |
| `period_notify_period` | Boolean | 月經來前通知開關 |
| `period_notify_ovulation` | Boolean | 排卵期前通知開關 |

---

### 2.4 ExpenseRecord（支出記錄）
| 欄位 | 型態 | 說明 |
|------|------|------|
| `user_id` | FK → User | |
| `timestamp` | String(20) | YYYY-MM-DD HH:MM:SS |
| `category` | String(50) | 類別名稱（無 emoji 前綴）|
| `note` | String(200) | 項目說明 |
| `amount` | Float | 金額 |

---

### 2.5 SalaryRecord（薪資記錄）
| 欄位 | 型態 | 說明 |
|------|------|------|
| `user_id` | FK → User | |
| `date` | String(10) | YYYY-MM-DD |
| `type` | String(20) | `'shift'` 或 `'bonus'` |
| `start_time` | String(5) | HH:MM（shift 用） |
| `end_time` | String(5) | HH:MM（shift 用） |
| `hours` | Float | 時數 |
| `rate` | Float | 時薪 |
| `amount` | Integer | 金額 |
| `note` | String(200) | 備註 |

---

### 2.6 PeriodRecord（生理期記錄）
| 欄位 | 型態 | 說明 |
|------|------|------|
| `user_id` | FK → User | |
| `start_date` | String(10) | YYYY-MM-DD |
| `end_date` | String(10) | YYYY-MM-DD（可 null） |
| `cycle_length` | Integer | 距離上次的天數 |
| `note` | String(255) | 備註 |
| `exclude_from_avg` | Boolean | 是否排除此次（異常週期） |

---

### 2.7 其他模型
| 模型 | 用途 |
|------|------|
| `Reminder` | 提醒事項（單次/每日/每週/每月，支援自訂星期） |
| `UserCalendar` | ICS 行事曆來源（URL 或上傳 .ics 檔） |
| `CalendarNotificationLog` | 行事曆通知去重紀錄 |
| `PeriodNotificationLog` | 生理期通知去重紀錄 |
| `ReportLog` | 月報發送紀錄 |
| `Countdown` | 倒數/週年紀念事件（支援每年自動重複） |
| `CountdownSubEvent` | 倒數事件的子里程碑 |

---

## 📱 Part 3: LINE Bot 系統 (LINE Bot System)

### 3.1 整體架構

```
使用者 LINE → LINE Server → /line/callback (Webhook)
                                ↓
                         line_routes.py
                                ↓
                     ┌─────────────────────┐
                     │  LineBinding 查找   │ ← 取代舊的 UserSettings.line_user_id
                     │  + 權限驗證         │
                     └─────────────────────┘
                                ↓
          ┌──────────┬──────────┬──────────┬──────────┐
          │ 記帳      │  薪資    │  月經    │  其他    │
          │(expense) │(salary)  │(period)  │(fallback)│
          └──────────┴──────────┴──────────┴──────────┘
```

### 3.2 LINE 多帳號綁定流程（v3.0）

1. 帳號擁有者在設定頁按「＋ 新增 LINE 帳號綁定」
2. 前端呼叫 `POST /auth/api/line-bindings/generate-code` → 回傳 6 位驗證碼（存於 `UserSettings.binding_code`，5 分鐘有效）
3. 對方在 LINE Bot 輸入驗證碼
4. Webhook 收到 → 查 `UserSettings.binding_code` 是否符合且未過期（比較 UTC vs UTC）
5. 驗證通過 → 建立 `LineBinding` 記錄，預設 nickname `使用者 N`，全權限
6. 設定頁輪詢（每 3 秒）偵測到新增 → 自動重整顯示

### 3.3 權限系統

```python
def has_perm(perm):
    perms = json.loads(binding.permissions or '[]')
    return perm in perms

# 使用範例（各指令前強制檢查）
if not has_perm("expense"):
    push_message("⛔ 此帳號無記帳權限...")
    return
```

### 3.4 智慧語意解析（Smart Parser）

| 格式 | 範例 | 對應功能 |
|------|------|----------|
| `記帳 [名稱] [金額]` | `記帳 午餐 120` | 新增支出，支援溯及日期如 `記帳 昨天 午餐 120` |
| `記帳 [名稱] [類別] [金額]` | `記帳 咖啡 飲食 55` | 指定類別 |
| `獎金 [金額] [時數?] [備註?]` | `獎金 5000 8 業績` | 新增獎金記錄 |
| `排班 [開始] [結束] [日期?]` | `排班 09:00 18:00 4/20` | 新增班表 |
| `查詢記帳 [月份?]` | `查詢記帳 4月` | 查詢並回傳當月（或指定月）總支出、分類統計與最新明細 |
| `查詢薪水 [月份?]` | `查詢薪水 4月` | 查詢並回傳當月（或指定月）總金額、時數與最新明細 |
| `月經` | `月經` | 今日開始 |
| `月經 4/15` | `月經 4/15` | 指定日期開始 |
| `月經 4/15 4/19` | `月經 4/15 4/19` | 指定區間 |
| `月經 結束` | `月經 結束` | 今日結束 |
| 其他/無法辨識 | 任意文字 | 回傳完整懶人包教學 |

### 3.5 管理 API（auth.py）

| Method | URL | 功能 |
|--------|-----|------|
| GET | `/auth/api/line-bindings` | 取得所有綁定列表 |
| POST | `/auth/api/line-bindings/generate-code` | 產生新的驗證碼 |
| PUT | `/auth/api/line-bindings/<id>` | 更新暱稱 & 權限 |
| DELETE | `/auth/api/line-bindings/<id>` | 移除綁定 |
| GET | `/auth/check_line_status` | 查詢已綁定數量（前端輪詢用）|

---

## ⏰ Part 4: 排程通知系統 (Scheduler)

使用 `Flask-APScheduler`，後端背景執行緒，每 60 秒掃描一次：

| 任務名稱 | 觸發條件 | 說明 |
|----------|----------|------|
| `check_reminders` | 每分鐘 | 比對目前時間 vs Reminder 設定，支援單次/每日/每週/每月 |
| `calendar_notify` | 每分鐘 | 每日依使用者自訂時間發送「明日行程總覽」 |
| `period_notify` | 每分鐘 | 每日 08:00 提前 N 天通知生理期即將到來 |
| `countdown_notify` | 每日 09:00 | 檢查釘選事件是否達到里程碑或到期日 |

**防重複機制**：`CalendarNotificationLog` & `PeriodNotificationLog`，依 `(user_id, date, key)` 唯一約束。

---

## 🧮 Part 5: 核心算法 (Core Algorithms)

### 5.1 生理期加權預測
- 取最近 6 筆紀錄，越新的佔比越高（6:5:4:3:2:1）
- 異常週期（< 14 天或 > 60 天）自動 `exclude_from_avg = True`
- 預測公式：`下次開始日 = 最近一次開始日 + 加權平均週期`
- 易孕期：`排卵日 ± 5 天`（排卵日 = 下次預測 - 14）

### 5.2 薪資國定假日加倍
- `tw_holidays.is_holiday(date)` 檢查（Google Calendar ICS + 勞基法白名單）
- 假日金額 = `hours × rate × 2`，備註自動加`【國定假日：XXX】`

### 5.3 記帳週期對齊
- 根據 `billing_cycle_start_day`（如 10）分組：`本月10日 ~ 下月9日`
- 超過 `budget_alert_threshold` (%) → 前端圖表轉橘/紅色警告

### 5.4 記帳分類 Emoji 渲染規則
- DB 存純文字類別（如 `飲食`）
- `expense.js` 透過 `emojiMap` 查表轉換：只有在 category 含空格（舊格式 `🍽️ 飲食`）時才取前綴，否則一律查 `emojiMap`

---

## 🔒 Part 6: 安全機制 (Security)

- **密碼**：`werkzeug.security.generate_password_hash`（Scrypt/PBKDF2-SHA256）
- **Session**：`Flask-Login`，Cookie 使用 `SECRET_KEY` 加密簽署，30天
- **API 驗證**：所有 API 均驗證 `current_user.id == resource.user_id`
- **LINE 驗證**：`X-Line-Signature` HMAC 校驗

---

## 🚀 Part 7: 開發與部署 (Workflow)

### 本地開發

```bash
cd /Users/weishichen/Documents/Program/python/工具箱/web_app
python app.py
```

### Git Push 流程

```bash
cd /Users/weishichen/Documents/Program/python/工具箱/web_app
git add .
git commit -m "feat(模組): 說明"
git push
```

> [!WARNING]
> **絕對不要**在外層 `python/` 或 `工具箱/` 執行 `git add .`！
> 外層可能有 `.git`，會把 venv 虛擬環境（數萬個檔案）全部掃描進去，導致終端卡死。

### PythonAnywhere 部署

```bash
# Bash console
git pull origin main

# 新版本有 DB 結構變更時：
python scripts/maintenance/migrate_XXX.py

# 最後必做：Web 頁面按 Reload 按鈕
```

### 初次部署（全新環境）

```bash
pip install -r requirements.txt
python scripts/maintenance/init_db.py  # 建立所有資料表
# 設定 .env 檔案後 Reload
```

---

## 📱 Part 8: 手機端設計規範 (Mobile Design)

### 8.1 響應式斷點

| 斷點 | 說明 |
|------|------|
| `≤ 768px` | 平板適度縮小，保持多欄 |
| `≤ 600px` | 手機主要優化區間 |
| `≤ 480px` | 字體進一步縮小 |
| `≤ 400px` | 極小螢幕最低可用尺寸 |

### 8.2 觸控目標

| 元素 | 最小尺寸 |
|------|----------|
| 按鈕 | 44 × 44 px |
| 輸入框高度 | 40 px |
| 列表項目 | 48 px |

### 8.3 常見問題

| 問題 | 解決方案 |
|------|----------|
| iOS 輸入框自動放大 | `font-size: 16px`（≥16px 不觸發） |
| 模態框超出畫面 | `max-height: 90vh` + 手機底部彈出 `border-radius: 24px 24px 0 0` |
| 拖動卡片誤觸 | `handle: '.drag-handle'`（限制拖動區域） |
| 橫向滾動條 | 避免 `width: 100px` 固定寬，改用 `flex: 1` |

---

## 📋 Part 9: 版本更新記錄 (Changelog)

### v3.1（2026-05-04）多帳號通知精準分流 + 智慧匯出與報表優化
- **通知底層重構**：`line_service.py` 實作 `push_to_user(user_id, msg, module)` 核心廣播方法，能依據每個綁定帳號的 `permissions` (如 `salary`, `expense`, `period`) 決定是否派發通知，並向下相容舊版 `UserSettings`。
- **全模組升級分流**：全面將薪資、記帳、生理期、行事曆、提醒事項與倒數日等後端自動排程推播，對接至 `push_to_user` 多帳號系統。
- **雙效匯出機制**：重構 `salary_routes.py` 與 `expense_routes.py` 的匯出 API。不再直接回傳 CSV 檔案，改為回傳 JSON（包含 `csv_content` 與傳送結果），前端攔截後同時跳出「已傳送對象名單」提示並自動觸發瀏覽器下載。
- **報表排版強化**：LINE 推播的薪資與記帳報表新增「使用者名稱」顯示，並在明細列表上方加入「項目/分類統計」區塊（自動加總各類別金額、筆數與排班總時數）。

### v3.0（2026-04-18）LINE 多帳號綁定 + 權限系統
- **新增 `LineBinding` 資料表**：一個網站帳號可綁定多個 LINE 帳號，每個帳號有獨立暱稱與權限清單
- **權限控制**：LINE Bot 收到指令前強制驗證 `has_perm()`，無權限回傳 ⛔ 提示
- **設定頁 UI**：多帳號清單、可折疊 QR Code 按鈕、權限 badge 切換（綠=開/紅刪除線=關）、失焦自動儲存
- **API**：`GET/POST/PUT/DELETE /auth/api/line-bindings`
- **遷移腳本**：`scripts/maintenance/migrate_line_bindings.py`（舊 `line_user_id` 一鍵升格）
- **Bug 修復**：記帳分類 Emoji 渲染錯誤（LINE 記帳與網頁記帳顯示不同圖示）
- **時區修正**：`binding_expiry` 比較改用純 UTC，修復驗證碼永遠過期的問題

### v2.6.2（2026-03-28）倒數卡片升級
- 首頁倒數卡片全新 Glassmorphism 漸層設計（週年 vs 倒數自動切換配色）
- 新增「下一個目標 (Next Up)」智慧追蹤（自動掃描子事件 & 里程碑）
- 修正「每年自動重複」無法持久儲存的 Bug

### v2.6（2026-03-28）倒數系統
- 新增 `repeat_annually` 欄位（Countdown & CountdownSubEvent）
- 智慧推算：過期日期自動推至今年/明年下一次
- 詳情頁行內編輯 Modal

### v2.5（2026-03-24）生理期追蹤
- 加權平均週期計算（最近 6 期，越新比重越高）
- 儀表板狀態橫幅、「今天開始/結束」一鍵按鈕
- FullCalendar 視覺化月曆（經期紅/易孕期淺綠/排卵日深綠）
- 生理期預測通知服務（APScheduler 每日 08:00）

### v2.4（2026-03-24）薪資 & 記帳修正
- 帳務週期計算改用 `billing_cycle_start_day` 正確分組
- 月曆手機版改用 CSS Grid `repeat(7, 1fr)` 修正對齊問題
- 歷史排班新增「此週期匯出」與「全部匯出」分開按鈕

### v2.3（2026-03）整合行事曆
- 支援訂閱 ICS URL & 上傳 .ics 檔案
- 每日自訂時間發送「明日行程總覽」通知
- 新增 `UserCalendar`、`CalendarNotificationLog` 資料模型

---

**文件維護建議**：每次有重大功能變更時，在「版本更新記錄」新增一節，並同步更新受影響的 Part 1 ~ Part 7 內容。
