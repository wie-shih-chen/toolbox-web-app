# 📊 工具箱 Web App - 完整架構總覽

> **最後更新**：2026-06-16 | **版本**：v4.2（整合日曆全功能升級：內建日曆顯示設定、顏色主題、顯示/隱藏切換）  
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
│   ├── ntut_routes.py              # 📅 整合行事曆（ICS 解析、多來源訂閱管理、內建日曆設定 API）
│   ├── reminder_routes.py          # 🔔 提醒事項 (單次 & 週期性提醒)
│   ├── download_routes.py          # 📥 影音下載器 (yt-dlp 任務)
│   ├── line_routes.py              # 📱 LINE Bot Webhook (智慧語意解析 & 推播)
│   ├── settings_api.py             # ⚙️ 設定專用 API (AJAX 非同步儲存)
│   ├── shop.py                     # 🛍️ 購物前台 (商品瀏覽 / 購物車 / 結帳流程)
│   └── admin.py                    # 🛠️ 商店後台 (商品管理 / ZIP 匯入匯出 / 訂單管理)
│
├── 🧠 services/ (服務層 - 商業邏輯)
│   ├── ai_chat_service.py          # ⭐ AI 核心服務 (Gemini 整合 / 意圖分析 / 狀態機邏輯)
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
│   ├── line_service.py             # LINE 訊息互動 (封裝 push_message 與 push_flex)
│   ├── flex_message_service.py     # 🎨 Flex UI 引擎（Carousel 輪播、QuickChart 趨勢圖、最近10筆記錄）
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
│   ├── shop/
│   │   ├── index.html              # 🛍️ 購物前台首頁 (商品展示)
│   │   ├── cart.html               # 🛒 購物車與結帳
│   │   └── orders.html             # 📦 前台我的訂單
│   │
│   ├── admin/
│   │   ├── dashboard.html          # 🛠️ 商店後台總覽
│   │   ├── products.html           # 📦 商品管理 (ZIP 匯入匯出)
│   │   ├── orders.html             # 📋 訂單管理與出貨
│   │   └── users.html              # 👤 會員權限管理
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
    ├── init_db.py                  # ⭐ 初始化所有資料表（首次部署必跑）
    ├── migrate_builtin_cal.py      # ⭐ v4.2 遷移：UserSettings 新增內建日曆欄位
    ├── migrate_ai_session.py       # v4.0 遷移：建立對話 Session 資料表
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
| `calendar_notify_enabled` | Boolean | 行事曆每日通知開關 |
| `calendar_notify_time` | String(5) | 通知時間 HH:MM |
| `builtin_salary_name` | String(50) | 班表日曆自訂名稱（預設「🏷 班表」） |
| `builtin_salary_color` | String(10) | 班表日曆自訂顏色（預設 `#6366f1`） |
| `builtin_period_name` | String(50) | 週期追蹤日曆自訂名稱（預設「🩸 週期追蹤」） |
| `builtin_period_color` | String(10) | 週期追蹤日曆自訂顏色（預設 `#ff4d4f`） |
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


### 2.8 LineConversationSession（對話狀態 Session）⭐ v4.0 新增
| 欄位 | 型態 | 說明 |
|------|------|------|
| `id` | Integer PK | |
| `line_user_id` | String(255) | 唯一索引，與 LINE 使用者綁定 |
| `state` | String(20) | `'IDLE'` (閒置) 或 `'COLLECTING'` (引導填寫中) |
| `intent` | String(50) | 當前任務，如 `'expense'`, `'shift'` |
| `collected_data` | Text (JSON) | 已收集的欄位資料 |
| `pending_fields` | Text (JSON) | 尚未填寫的欄位清單 |
| `last_activity` | DateTime | 用於 30 分鐘逾時自動重置 |

---

## 📱 Part 3: LINE Bot 系統 (LINE Bot System)

### 3.1 AI 處理流程 (7-Step State Machine) ⭐ v4.1 重構

當 LINE 收到訊息時，會進入以下狀態機流程（**已全面由 AI 接管，移除所有手動快速通道**）：

1. **身分識別**：根據 `line_user_id` 查找 `LineBinding` 與 `LineConversationSession`。
2. **指令預處理**：
   - 若輸入「取消/算了/不用了」→ 清除 Session，回到 IDLE。
3. **狀態分流**：
   - **COLLECTING 模式**（正在填寫中）：
     - 先呼叫 Gemini AI 分析輸入（附帶 `current_intent` 上下文提示）
     - 若 AI 返回 `error`（如 Rate Limit）→ 啟動 **`fallback_extract`** 本地規則引擎降級解析
     - 更新 `collected_data`，若齊全 → 寫入 DB，若仍缺 → 繼續追問
   - **IDLE 模式**：
     - 僅保留兩條非 AI 快速通道（節省 API 額度）：
       - `查詢記帳 / 查詢薪水`（固定格式查詢）
       - `查詢`（顯示 LINE User ID）
     - 其餘所有輸入全部送交 Gemini AI 分析（`analyze_intent`）
       - 查詢類 → 呼叫 `execute_query` 回傳 Flex 卡片
       - 寫入類 + 資料齊全 → 直接寫入 DB
       - 寫入類 + 缺資料 → 切換至 **COLLECTING** 模式，開始引導追問
       - `chat` 類 → 回傳 AI 自然語言回覆
       - `unknown` → 回傳 Flex Carousel 說明卡片

### 3.2 多月份範圍查詢與圖表分析 (Trend Analysis) ⭐ v4.0 新增

當使用者詢問範圍（如「2到5月的薪水」）時：
1.  **AI 解析**：Gemini 將口語解析為時間範圍（如 `start_month=2, end_month=5`）。
2.  **資料聚合**：`execute_query` 循環查詢各月統計。
3.  **UI 渲染**：
    *   使用 **Carousel (輪播)** 呈現：每個月一張獨立的精緻卡片。
    *   **趨勢圖卡片**：在輪播最後追加一張使用 **QuickChart API** 生成的折線圖，視覺化波動走勢。

### 3.3 LINE 多帳號綁定流程（v3.0）

1. 帳號擁有者在設定頁按「＋ 新增 LINE 帳號綁定」
2. 前端呼叫 `POST /auth/api/line-bindings/generate-code` → 回傳 6 位驗證碼（存於 `UserSettings.binding_code`，5 分鐘有效）
3. 對方在 LINE Bot 輸入驗證碼
4. Webhook 收到 → 查 `UserSettings.binding_code` 是否符合且未過期（比較 UTC vs UTC）
5. 驗證通過 → 建立 `LineBinding` 記錄，預設 nickname `使用者 N`，全權限
6. 設定頁輪詢（每 3 秒）偵測到新增 → 自動重整顯示

### 3.4 權限系統

```python
def has_perm(perm):
    perms = json.loads(binding.permissions or '[]')
    return perm in perms

# 使用範例（各指令前強制檢查）
if not has_perm("expense"):
    push_message("⛔ 此帳號無記帳權限...")
    return
```

### 3.5 智慧語意解析（Smart Parser）

| 格式 | 範例 | 對應功能 |
|------|------|----------|
| **AI 全接管** | `記帳` | AI 引導追問「項目名稱」→「金額」→ 存入 DB |
| **AI 全接管** | `我要記帳` | AI 辨識意圖為 expense，開始引導填寫 |
| **AI 全接管** | `昨天買咖啡85元` | AI 自動識別 expense，推算日期，直接寫入 |
| **AI 全接管** | `排班` | AI 引導追問「上班時間」→「下班時間」→ 存入 DB |
| **AI 全接管** | `下午2到6點打工` | AI 識別為 shift，解析時間段 |
| **AI 全接管** | `月經來了肚子痛` | AI 識別為 period start，記錄今日 |
| **AI 全接管** | `幫我記一個倒數到聖誕節` | AI 識別為 countdown，引導填寫名稱/日期 |
| **AI 全接管** | `2到5月的薪水` | AI 識別為 query_salary，回傳多月份輪播卡片 |
| `查詢記帳 [月份?]` | `查詢記帳 4月` | 固定格式快速查詢，不耗費 AI 額度 |
| `查詢薪水 [月份?]` | `查詢薪水 4月` | 固定格式快速查詢，不耗費 AI 額度 |
| 其他/無法辨識 | 任意文字 | AI 閒聊回覆，若實在無法處理才顯示說明卡片 |

### 3.6 管理 API（auth.py）

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

## 🎨 Part 10: Flex UI 與外部整合

### 10.1 QuickChart 整合規範
- **用途**：用於生成 LINE 卡片內的統計趨勢圖表。
- **URL 格式**：`https://quickchart.io/chart?bkg=transparent&c={CONFIG}`
- **安全建議**：圖表不包含敏感個資，僅顯示月份標籤與金額數值。

---

## 📋 Part 11: 版本更新記錄 (Changelog)

### v4.2（2026-06-16）整合日曆全功能升級

#### 內建日曆顯示設定
- **UserSettings 新增欄位**：`builtin_salary_name/color`、`builtin_period_name/color`，允許自訂班表與週期追蹤的顯示名稱與顏色。
- **新增設定 API**：`GET/PUT /ntut/internal/<type>/settings`（`type` = `salary` | `period`）。
- **編輯 Modal**：日曆側邊欄的 ✏️ 按鈕改為彈出編輯視窗（而非跳頁），可即時修改名稱與顏色，儲存後月曆立即更新。
- **DB Migration**：`migrate_builtin_cal.py`，執行 `python migrate_builtin_cal.py` 自動補齊欄位。

#### 日曆顏色實現原理
- **班表事件**：`display: 'block'`（強制月視圖以彩色方塊顯示，而非預設的點+文字）+ 事件層 `backgroundColor` 從 `UserSettings` 讀取。
- **週期事件分類著色**：
  - `history`（歷史經期）→ 使用者主題色實心
  - `predicted_period`（預測經期）→ 主題色 20% 半透明底色 + 實線邊框（`_hex_to_rgba()` 輔助函數轉換）
  - `fertile_window`、`ovulation` → 保留原本語意顏色（綠色系）
- **顏色正確套用原則**：FullCalendar 的事件層 `backgroundColor` 優先於 EventSource 的 `color`，因此必須在後端事件 JSON 中直接設定正確顏色。

#### 日曆顯示/隱藏切換
- **觸發方式**：點擊側邊欄的彩色圓點 (`.cal-dot`) 切換可見性。
- **視覺反饋**：隱藏時圓點變空心輪廓 (`boxShadow: inset 0 0 0 2px color`)，列表項目半透明（opacity 0.45）。
- **持久化**：狀態存 `localStorage`（key: `calVis_v1`），重整頁面後保持。
- **技術實現**：`toggleBuiltinVisibility(type)` / `toggleSubscribedVisibility(id)` + `_applyVis()` 輔助函數；`calSourceMap` 快取訂閱日曆的 URL 與顏色，以便重新加回 EventSource。

#### 通知設定頁更新
- `settings.html` 的「個別日曆設定」區塊現在也顯示班表與週期追蹤的靜音開關（原只有訂閱日曆）。

### v4.1（2026-05-10）AI 全接管架構：移除手動快速通道 + 規則降級備援 + Flex 卡片優化
- **AI 全面接管**：移除所有手動快速通道（記帳/排班/獎金/月經/倒數等關鍵字的 if/else 規則），現在所有訊息一律透過 Gemini AI 進行意圖分析，讓互動更自然靈活。
- **當前意圖上下文注入**：`analyze_intent` 新增 `current_intent` 參數，在 COLLECTING 狀態下會強制告知 AI 當前正在進行的操作（如 `expense`），避免 AI 遺忘上下文導致重複追問相同欄位。
- **`fallback_extract` 降級備援**：新增本地規則引擎，當 Gemini API Rate Limit 或網路錯誤時，系統不再顯示錯誤訊息，而是自動用本地規則從使用者輸入中提取關鍵欄位（支援 expense / shift / bonus / period / countdown），確保 COLLECTING 狀態下永遠不會被卡死。
- **Gemini 模型選用**：當前使用 `gemini-2.5-flash`（Free Tier 5 RPM / 20 RPD），視帳號情況可更換。建議開啟付費方案（Pay As You Go）以解除每日 20 次限制。
- **Flex 卡片優化**：
  - 記帳/薪資查詢卡片從「最近 5 筆」升級為「最近 10 筆」
  - 修正「查看全部記錄 →」按鈕的 404 錯誤（URL 補上尾部斜線 `/expense/` / `/salary/`）

### v4.0（2026-05-10）AI 對話管家 2.0：引導式填寫 + 多輪對話 + 趨勢分析
- **多輪對話狀態機**：引入 `LineConversationSession`，支援資料缺漏時 AI 主動引導填寫，不再因為一句話沒說清楚而失敗。
- **時間範圍查詢**：支援跨月份查詢（例如「前三個月的記帳」），自動解析起始與結束時間。
- **視覺化趨勢分析**：
  - 整合 **QuickChart API** 生成折線圖。
  - 多月份查詢自動回傳 **Carousel 輪播卡片**。
  - 薪資（藍色趨勢）與支出（粉色趨勢）配色區分。
- **底層優化**：
  - 修正了 `_get_date_range` 在跨年與 list 格式下的解析穩定性。
  - 解決了 Flex 訊息 JSON 包裝過深導致的 `OSError: write error` 問題。
  - 增加 30 分鐘會話逾時機制。

### v3.2（2026-05-07）AI 智慧管家 + Flex Message 視覺化 UI 升級
- **Gemini AI 全面接管**：整合 Google Gemini 2.0 Flash 進行自然語言解析。AI 具備「時間感知 (Temporal Awareness)」，能精準推算「昨天」、「上週五」等相對日期，並處理記帳、排班、獎金與生理期四類口語記錄。
- **Flex Message UI 2.0**：新增 `FlexMessageService` 專職負責建構高品質 UI。所有成功回饋（記帳、薪資）與查詢總覽（月度報告）全面從純文字升級為「收據風格」與「深色主題」的 Flex 卡片。
- **互動式教學卡片**：將原本雜亂的純文字說明升級為「多張滑動 Carousel 說明卡片」，並包含 AI 功能導覽。
- **穩定性優化**：修復了因內部函式重複 import 導致的 `UnboundLocalError`，並移除不相容的 LINE SDK 頂層引用。

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


MongoDB Atlas：
帳號：randy940907_db_user
密碼：vQ6E0jxF7D1x0s1d