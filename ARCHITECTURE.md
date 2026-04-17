# 📊 工具箱 Web App - 完整架構總覽

這份文件整合了所有專案架構資訊，包含檔案結構、頁面結構、資料模型與 API 設計。

---

## 📂 Part 1: 專案檔案結構 (Project File Structure)

完整的檔案與資料夾配置圖：

```
## 📂 Part 2: 專案檔案結構 (File Structure & Modules)

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

## 🔒 Part 6: 安全性與認證 (Security & Authentication)

專案採用工業標準的安全實踐，保護使用者資料：

### 6.1 密碼安全
- **加密演算法**：使用 `werkzeug.security.generate_password_hash`。預設採用 **Scrypt** 或 **PBKDF2-SHA256**（取決於系統支援），具備強大的抗暴力破解能力。
- **雜湊 (Hashing)**：資料庫中僅儲存雜湊值，永不儲存明文密碼。

### 6.2 認證機制
- **Session 管理**：基於 `Flask-Login`。
- **Cookie 安全**：`REMEMBER_COOKIE_DURATION` 預設為 30 天，且使用 `SECRET_KEY` 加密簽署。
- **登入保護**：
  - 非登入狀態訪問受限頁面將重導向至 `/login`。
  - 使用 `@login_required` 裝飾器。
  - 資料存取權限：所有 API 與資料查詢均嚴格驗證 `user_id == current_user.id`。

---

## ⏰ Part 7: 通知與排程系統 (Notification & Scheduler System)

使用 `Flask-APScheduler` 構建的多層次排程系統：

### 7.1 排程器配置
- **執行方式**：後端背景線程（BackgroundScheduler）。
- **輪詢頻率**：全域每 60 秒檢查一次（`interval: 60s`）。

### 7.2 任務詳情
- **🔔 自訂提醒 (`check_reminders`)**：
    - 比對目前的「日期 + 時間 (HH:MM)」與 `Reminder` 設定。
    - 支援「單次、每天、每週、每月」四種頻率。
- **📅 行事曆通知 (`calendar_notify`)**：
    - 每日檢查是否有使用者設定的通知時間（如預設 20:00）。
    - 提前一天發送「明日行程總覽」。
- **🩸 生理期預測通知 (`period_notify`)**：
    - 每日檢查通知時間（如預設 08:00）。
    - 提早 X 天提醒生理期即將到來。
- **⏳ 倒數里程碑通知 (`countdown_notify`)**：
    - 每日 09:00 (TW) 檢查是否有釘選的任務達到重要里程碑或目標日期。

### 7.3 防重複機制
為確保重啟伺服器或多線程情況下不重複發送通知，使用日誌記錄表：
- `CalendarNotificationLog` & `PeriodNotificationLog`。
- 檢查 `(user_id, target_date, event_key)` 唯一性後才發送。

---

## 🧠 Part 8: 核心算法說明 (Core Logic & Algorithms)

### 8.1 薪資加倍算法 (Double Salary)
- **觸發條件**：`services.tw_holidays.is_holiday(date)` 回傳非空名稱。
- **邏輯**：
    - 計算時數 `hours` = `end_time - start_time - break_minutes`。
    - 若為國定假日，金額 = `hours * hourly_rate * 2`。
    - 自動在備註欄加上 `【國定假日：XXX】工資加倍（...）` 前綴。

### 8.2 生理期預測模型 (Weighted Prediction)
- **計算平均週期**：
    - 取最近 **6 個月** 的紀錄。
    - **權重分配**：最新一筆權重最高 (6)，最遠權重最低 (1)。
    - **異常值過濾**：排除 < 14 天或 > 60 天的極端週期，若 > 60 天則自動標記為 `exclude_from_avg = True`。
- **預測點計算**：
    - `下次開始日` = `本次開始日 + 平均週期`。
    - `易孕期` = `排卵日 ± X 天`（其中排卵日為 `下次預測開始日 - 14 天`）。

### 8.3 記帳週期對齊 (Billing Cycle Alignment)
- **動態切片**：根據 `billing_cycle_start_day` (如每月 10 日)，將資料動態分組為 `當月 10 日 ~ 下月 9 日`。
- **預算警戒**：
    - 計算 `當前週期總支出 / monthly_budget`。
    - 超過 `budget_alert_threshold` (%) 時，前端圖表轉變為警告色（橘/紅）。

---

## 📱 Part 9: 外部整合 (External Integrations)

### 9.1 LINE Bot 互動流程
- **綁定流程**：
    1. 使用者在網頁生成 6 位數「驗證碼」。
    2. LINE 輸入驗證碼後，後端透過 Webhook 將 `line_user_id` 寫入 `UserSettings`。
- **主動推送**：整合 `LineService.push_message()`，支援純文字與 Flex Message (彩色訊息卡片)。

### 9.2 影音下載邏輯
- **支援庫**：`yt-dlp`。
- **處理流程**：同步請求 -> 後端啟動獨立進程執行 -> 下載至 `/downloads` -> 通知使用者。
- **清理機制**：定期清除超過 24 小時的暫存檔案。
**後端框架** | Flask 3.x                         |
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
- ⚠️ 注意：根目錄下的 `expense_data.json` 與 `salary_data.json` 已全數遷移至資料庫並刪除，不再使用。

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
**專案版本**: v2.6

### v2.6.2 更新摘要 (2026-03-28)
- **首頁倒數卡片極致視覺化 (VIP Redesign)**：
  - 全新 Glassmorphism 璃光卡片設計：根據「週年紀念」或「目標倒數」自動切換多重層次漸層色背景（如櫻粉至火紅、湛藍至潮汐紫）。
  - **下一個目標 (Next Up) 智慧追蹤**：卡片底部新增「下一個目標」區區塊，自動掃描所有子事件與系統里程碑（如 500 天、1000 天、5 週年），顯示最近的目標名稱與剩餘天數。
  - **操作體驗優化**：修正「每年自動重複」勾選後無法持久儲存的 Bug，透過後端布林值強制轉型提升資料穩定度。

### v2.6 更新摘要 (2026-03-28)
- **倒數日與紀念日 (Countdown) 升級**：
  - **每年自動重複功能**：`Countdown` 與 `CountdownSubEvent` 模型新增 `repeat_annually` 布林值欄位。
  - **智慧推算邏輯**：勾選「每年自動重複」的事件，若日期已過，系統會自動推算至今年或明年的下一次紀念日，儀表板永遠顯示最近一次的到期天數。
  - **首頁卡片捷徑優化**：點擊首頁上方的釘選倒數卡片，將直接跳轉至該事件的獨立里程碑時間軸（詳情頁），而非清單頁面。
  - **行內編輯體驗**：在詳情頁嵌入「編輯事件」彈出式視窗，以及新增子事件勾選框，無需跳轉即可快速管理。

### v2.5 更新摘要 (2026-03-24)
- **新增 🩸 生理期追蹤器**：依照醫學標準算法推算下次經期、易孕期 (排卵日前5後1天) 與排卵日。
- **資料庫層**：新增 `PeriodRecord` 模型與 `UserSettings` 中的 `avg_period_cycle` / `avg_period_duration`。
- **後端介面**：新增 `/period/` 系列路由與 API 端點 (`events`, `records`)，自動處理紀錄間隔天數的平均值。
- **前端介面**：使用 `FullCalendar` 實作視覺化月曆，紅色標示經期、淺綠標示易孕期、深綠標示排卵日；首頁與選單加入專屬捷徑。
- **介面優化 (v2.5.1)**：
  - 新增歷史紀錄填空列表，支援快速新增與圖示編輯，大幅提升手機端操作便利性。
  - 修正日曆顯示邏輯：新增紀錄若未填寫結束時間，日曆上僅顯示為單日，避免被誤認為預設天數。
  - 優化日曆事件顏色：調整易孕期與排卵日的色彩透明度，確保在深色模式下文字依然清晰可見。

### v2.5.2 更新摘要 (2026-03-27)
- **生理期追蹤器精準度提升**：
  - 改用「加權平均」計算週期長度，越近期的週期佔比越重（6:5:4:3:2:1）。
  - 將手動設定的「平均經期天數」改為從實際紀錄中的（結束日-開始日）自動推算加權平均值。
- **生理期追蹤器體驗優化**：
  - 儀表板新增「目前狀態橫幅」，顯示經期第幾天或距離下次的天數與易孕期。
  - 新增「🩸 今天開始」與「✅ 今天結束」一鍵快選按鈕，並根據當前狀態自動禁用不合理的選項。
  - 設定頁面移除手動儲存按鈕，改為防抖自動儲存（Auto-Save），並帶有狀態提示小標籤。
- **介面調整**：
  - 將手機端底部導覽列的「生理期」捷徑移除以節省空間，改由首頁入口進入。
  - 修正後端 `get_summary` 分析跨日資料時，結束日期條件包容過大導致的顯示錯誤。

---

### v2.4 更新摘要 (2026-03-24)

#### 薪水小幫手
- **匯出按鈕重整**：本週排班頁移除匯出按鈕；歷史排班改為兩個並排按鈕「📅 此週期匯出」與「📤 匯出全部」
- **新增 `/salary/api/export-period?period=YYYY-MM` 端點**：只匯出指定月份週期 CSV，同樣支援 Email/LINE/Download
- **修正帳務週期計算 (`get_monthly_periods`)**：原先產生日曆月週期 (1日~月底)，現根據 `billing_cycle_start_day` 產生正確週期（例：設10 → `02/10 ~ 03/09`）
- **修正月曆手機版格子對齊**：`monthly.html` 改用 CSS Grid `repeat(7, 1fr)`，解決手機上格子大小不一、無法與星期標題對齊的問題

#### 記帳工具
- **修正帳務週期末日被排除的 Bug**：`expense_service.py` `get_summary()` 過濾改用 `<=`（含），確保週期最後一天（如 3/9）資料正確歸入當期
- **修正週期概覽跨期週別顯示**：當週別（週一至週日）跨越帳單週期基準日時，卡片與明細標題會自動裁切至實際週期邊界（例如帳單日為 10 號，第一週顯示 `02/10 ~ 02/15`、最後一週顯示 `03/09 ~ 03/09`），解決長週超出本期範圍造成的視覺誤區

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

---

## 📱 Part 3: 全域導覽列 (Global Navigation)

專案採用雙軌導覽設計，確保在桌面端與行動端均有良好體驗：

### 1. 桌面端導覽 (Top Bar)
- 定義於 `base.html` 的 `.nav-bar.glass` 中。
- 包含品牌 Logo、提醒通知鈴鐺、個人設定及登出按鈕。

### 2. 行動端底部導覽 (Mobile Bottom Nav)
- **核心模組**：僅保留 4 個最核心的入口以確保間距舒適：
  1.  🏠 **首頁** (`main.index`)
  2.  💵 **薪資** (`salary.index`)
  3.  📅 **日曆** (`ntut.calendar`)
  4.  📒 **記帳** (`expense.today`)
- **技術注記**：
  - **獨立層級**：為了防止個別頁面標籤未閉合（如 `index.html` 的 `div` 遺失）導致導覽列隱藏，導覽列已移至 `base.html` 的 `.container` 容器**之外**，直接作為 `body` 的子元素並配合 `position: fixed` 定位。
  - **安全距離**：所有需要滾動的頁面應在內容區底部保留至少 `80px` 的 `padding` (或由 `.container` 的 `75px` bottom padding 覆蓋)，避免內容被導覽列遮擋。
  - **生理期/倒數**：為節省底部空間，這兩個模組不列入常駐導航，需從首頁入口進入。

---

## 🚀 Part 4: 開發與部署流程 (Workflow)

### 1. 版本控制原則專案的 Github 儲存庫 (`toolbox-web-app.git`) 綁定於 `工具箱/web_app` 資料夾中。

### 正確的上傳（Push）流程

每次開發或修改完成後，請**務必**進入 `web_app` 資料夾內，再執行 Git 指令。

```bash
# 1. 切換到真正綁定 Github 的專案目錄
cd /Users/weishichen/Documents/Program/python/工具箱/web_app

# 2. 將所有修改加入暫存區
git add .

# 3. 提交變更 (替換為自己的說明)
git commit -m "feat(標籤): 更新內容說明"

# 4. 推送上雲端
git push
```

> [!WARNING]
> **切勿在外層目錄執行 Git 指令**
> 絕對不要在外層目錄 (`python/` 或 `工具箱/`) 執行 `git add .`！因為外層可能也有建立過 `.git` 紀錄，若在外層執行，Git 會把外層所有的爬蟲專案、`venv` 虛擬環境（好幾萬個暫存檔）全部掃描進去，導致終端機直接卡住甚至癱瘓。
