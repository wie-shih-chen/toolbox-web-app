"""
AI Chat Service
================
處理 LINE Bot 的多輪 AI 對話邏輯：
1. analyze_intent()       — 呼叫 Gemini 分析意圖 + 已知欄位
2. get_missing_fields()   — 計算此意圖缺少哪些必填欄位
3. build_question()       — 生成友善的追問訊息
4. execute_write()        — 執行資料寫入（expense/shift/bonus/period）
5. execute_query()        — 執行資料查詢，回傳 Flex 或文字
"""

import json
import calendar as cal_module
from datetime import datetime, timedelta
from flask import current_app


# ─────────────────────────────────────────────────────────────
# 各 intent 的必填欄位定義
# ─────────────────────────────────────────────────────────────
REQUIRED_FIELDS = {
    'expense': ['name', 'amount'],
    'shift':   ['start_time', 'end_time'],
    'bonus':   ['amount'],
    'period':  ['type'],  # type = 'start' or 'end'
}

# 每個欄位對應的追問問題（繁體中文，口語化）
FIELD_QUESTIONS = {
    'name':       '這次消費的項目是什麼？（例如：午餐、珍珠奶茶、交通費）',
    'amount':     '金額是多少呢？',
    'category':   '想歸類到哪個類別？\n可選：飲食、交通、娛樂、居住、其他\n（直接輸入類別名稱，或按 Enter 略過用「飲食」）',
    'start_time': '幾點開始上班呢？（例如：14:00 或 1400）',
    'end_time':   '幾點下班呢？（例如：19:00 或 1900）',
    'type':       '是月經開始還是結束呢？\n請回覆「開始」或「結束」',
}


# ─────────────────────────────────────────────────────────────
# 月份範圍輔助函式（複製自 line_routes，避免循環引用）
# ─────────────────────────────────────────────────────────────
def _get_date_range(data):
    """從 AI 資料中計算正確的日期範圍（支援單月、多月範圍）。"""
    now = datetime.utcnow() + timedelta(hours=8)
    y = data.get('year') or now.year
    
    start_m = data.get('start_month') or data.get('month')
    end_m = data.get('end_month') or data.get('month')
    
    # 若皆無，預設本月
    if start_m is None: start_m = now.month
    if end_m is None: end_m = now.month
    
    # 處理 list 情況
    if isinstance(start_m, list): start_m = start_m[0]
    if isinstance(end_m, list): end_m = end_m[-1]
    
    try:
        start_m = int(start_m)
        end_m = int(end_m)
    except:
        start_m = end_m = now.month

    # 跨年邏輯：如果查詢月份 > 現在月份，視為去年
    if start_m > now.month and data.get('year') is None:
        y -= 1
        
    last_day = cal_module.monthrange(y, end_m)[1]
    
    label = f"{start_m}月" if start_m == end_m else f"{start_m}月 ~ {end_m}月"
    return f"{y}-{start_m:02d}-01", f"{y}-{end_m:02d}-{last_day}", label


# ─────────────────────────────────────────────────────────────
# 1. 意圖分析（呼叫 Gemini）
# ─────────────────────────────────────────────────────────────
def analyze_intent(msg, collected_data, perms, gemini_key):
    """
    呼叫 Gemini API 分析使用者輸入，回傳：
    {
      "action": "expense|shift|bonus|period|query_expense|query_salary|query_period|query_balance|cancel|unknown",
      "data": { ...已知欄位... },
      "missing_fields": [...],
      "confidence": "high|medium|low"
    }
    出現任何例外則回傳 {"action": "unknown"}
    """
    now_dt = datetime.utcnow() + timedelta(hours=8)
    now_str = now_dt.strftime('%Y-%m-%d %H:%M')
    weekday_map = {1: '一', 2: '二', 3: '三', 4: '四', 5: '五', 6: '六', 7: '日'}
    weekday = weekday_map[now_dt.isoweekday()]
    collected_json = json.dumps(collected_data, ensure_ascii=False) if collected_data else '{}'
    perms_str = '、'.join(perms) if perms else '（無）'

    prompt = f"""你是個人工具箱的 AI 助手，能提取使用者說話中包含的資料。
現在時間：{now_str}（星期{weekday}）
使用者說：「{msg}」
對話上下文（已收集的資料）：{collected_json}
使用者的功能權限：{perms_str}

你的任務：分析這句話，判斷是「寫入」還是「查詢」，或是「取消」，或是需要自由「閒聊/問答」。

===【查詢類（直接回傳資料，不需追問）】===
- query_expense：查詢記帳總覽。
  - 欄位：month (單月), start_month, end_month (範圍), year
  - 範例：「上個月」→ month=上月數字；「2到5月」→ start_month=2, end_month=5
- query_salary：查詢薪資總覽。
  - 欄位：month, start_month, end_month, year
- query_period：查詢生理期預測（下次日期、排卵期等）
- query_balance：查詢本週期剩餘預算
- query_countdown：查詢即將到來的倒數日與紀念日

===【寫入類（可能需要追問缺少欄位）】===
✅ expense（支出記帳）：
  - 必填：name（項目名稱）、amount（金額，數字）
  - 選填：category（類別：飲食/交通/娛樂/居住/其他，預設飲食）、date（YYYY-MM-DD，預設今天）

✅ shift（排班打工）：
  - 必填：start_time（HH:MM）、end_time（HH:MM）
  - 選填：date（YYYY-MM-DD，預設今天）、note

✅ bonus（獎金）：
  - 必填：amount（數字）
  - 選填：date（YYYY-MM-DD，預設今天）、note

✅ period（生理期）：
  - 必填：type（"start" 或 "end"）
  - 選填：date（YYYY-MM-DD，預設今天）、note

===【特殊情況】===
- cancel：使用者說「取消」「算了」「不用了」→ 中止對話
- chat：無法明確歸類於上述查詢/寫入意圖，或是使用者只是在閒聊、提問（例如「我要記帳」卻沒給任何資訊時，可以直接回覆引導他）。請將你貼心、口語化的回覆放在 "reply" 欄位，並將 action 設為 "chat"。

===【時間推算】===
若提到「昨天」「上週五」「前天」，根據現在時間 {now_str}（星期{weekday}）推算正確的 YYYY-MM-DD。
若未提到時間，date 欄位留空（不要填 null，直接省略）。

回傳 JSON（不要加 ```json 標籤）：
{{
  "action": "...",
  "data": {{ ...已知欄位... }},
  "missing_fields": [...尚缺的必填欄位名稱...],
  "confidence": "high|medium|low",
  "reply": "給使用者的自然語言回覆（僅當 action 為 chat 時提供）"
}}"""

    try:
        from google import genai
        client = genai.Client(api_key=gemini_key)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        res_text = response.text.strip()
        # 清理可能的 markdown code block
        if res_text.startswith('```'):
            res_text = res_text.split('\n', 1)[1] if '\n' in res_text else res_text[3:]
        if res_text.endswith('```'):
            res_text = res_text[:-3]
        return json.loads(res_text.strip())
    except Exception as e:
        current_app.logger.error(f"[AIChatService] Gemini 分析失敗: {e}")
        return {"action": "unknown"}


# ─────────────────────────────────────────────────────────────
# 2. 計算缺少的必填欄位
# ─────────────────────────────────────────────────────────────
def get_missing_fields(intent, collected_data):
    """
    回傳此 intent 中，collected_data 尚未包含的必填欄位清單。
    """
    required = REQUIRED_FIELDS.get(intent, [])
    return [f for f in required if not collected_data.get(f)]


# ─────────────────────────────────────────────────────────────
# 3. 生成追問訊息
# ─────────────────────────────────────────────────────────────
def build_question(field):
    """根據欄位名稱回傳友善的追問文字。"""
    return FIELD_QUESTIONS.get(field, f'請提供「{field}」的資訊：')


# ─────────────────────────────────────────────────────────────
# 4. 執行資料寫入
# ─────────────────────────────────────────────────────────────
def execute_write(intent, data, user_obj, setting, has_perm_fn):
    """
    依 intent 寫入對應的資料庫記錄。
    回傳 tuple: ('flex'|'text', payload, alt_text) 或 ('error', error_msg, None)
    """
    from services.flex_message_service import FlexMessageService

    now_dt = datetime.utcnow() + timedelta(hours=8)

    if intent == 'expense':
        if not has_perm_fn('expense'):
            return ('error', '⛔ 此帳號無記帳權限，請聯絡帳號擁有者開啟。', None)

        name = data.get('name', '隨手記')
        amount = float(data.get('amount', 0))
        category = data.get('category', '飲食')
        date_str = data.get('date', now_dt.strftime('%Y-%m-%d'))
        record_time = f"{date_str} {now_dt.strftime('%H:%M:%S')}"

        from models import ExpenseRecord, db
        new_rec = ExpenseRecord(
            user_id=user_obj.id, timestamp=record_time,
            category=category, amount=amount, note=name
        )
        db.session.add(new_rec)
        db.session.commit()

        flex = FlexMessageService.build_expense_confirm(
            name=name, amount=amount, category=category, timestamp=record_time, ai=True
        )
        return ('flex', flex, f'AI 記帳：{name} ${amount:g}')

    elif intent == 'shift':
        if not has_perm_fn('salary'):
            return ('error', '⛔ 此帳號無薪資管理權限，請聯絡帳號擁有者開啟。', None)

        start_time = _fmt_time(data.get('start_time', '09:00'))
        end_time   = _fmt_time(data.get('end_time', '18:00'))
        if not (start_time and end_time):
            return ('error', '❌ 時間格式有誤，請重新輸入（例如：14:00）', None)

        date_str = data.get('date', now_dt.strftime('%Y-%m-%d'))
        note = data.get('note', '')

        t1 = datetime.strptime(start_time, '%H:%M')
        t2 = datetime.strptime(end_time, '%H:%M')
        if t2 < t1:
            t2 += timedelta(days=1)
        hours = (t2 - t1).total_seconds() / 3600.0
        rate = float(setting.hourly_rate or 196.0)

        from services.salary_service import _apply_holiday_pay
        effective_rate, amount, updated_note = _apply_holiday_pay(date_str, rate, hours, note)

        from models import SalaryRecord, db
        new_rec = SalaryRecord(
            user_id=user_obj.id, date=date_str, type='shift',
            start_time=start_time, end_time=end_time,
            hours=hours, rate=effective_rate, amount=amount, note=updated_note
        )
        db.session.add(new_rec)
        db.session.commit()

        flex = FlexMessageService.build_salary_confirm(
            record_type='shift', date=date_str, amount=amount, hours=hours,
            start_time=start_time, end_time=end_time, note=updated_note, ai=True
        )
        return ('flex', flex, f'AI 排班：{date_str} {start_time}~{end_time}')

    elif intent == 'bonus':
        if not has_perm_fn('salary'):
            return ('error', '⛔ 此帳號無薪資管理權限，請聯絡帳號擁有者開啟。', None)

        amount = int(float(data.get('amount', 0)))
        date_str = data.get('date', now_dt.strftime('%Y-%m-%d'))
        note = data.get('note', '')

        from models import SalaryRecord, db
        new_rec = SalaryRecord(
            user_id=user_obj.id, date=date_str, type='bonus',
            amount=amount, hours=0, note=note
        )
        db.session.add(new_rec)
        db.session.commit()

        flex = FlexMessageService.build_salary_confirm(
            record_type='bonus', date=date_str, amount=amount, note=note, ai=True
        )
        return ('flex', flex, f'AI 獎金：${amount:,}')

    elif intent == 'period':
        if not has_perm_fn('period'):
            return ('error', '⛔ 此帳號無生理期紀錄權限，請聯絡帳號擁有者開啟。', None)

        ptype = data.get('type', 'start')
        date_str = data.get('date', now_dt.strftime('%Y-%m-%d'))
        note = data.get('note', '')

        from services.period_service import PeriodService
        period_svc = PeriodService(user_obj.id)

        if ptype == 'end':
            history = period_svc.get_history()
            latest = history[0] if history else None
            if not latest or latest['end_date']:
                return ('error', '❌ 目前沒有進行中的生理期可以結束喔！', None)
            period_svc.update_record(
                latest['id'], start_date=latest['start_date'],
                end_date=date_str, note=latest['note']
            )
            msg = f'✨ 生理期結束紀錄\n📅 結束日期：{date_str}'
            if note:
                msg += f'\n📝 備註：{note}'
            return ('text', msg, None)
        else:
            result = period_svc.add_record(start_date=date_str, end_date=None, note=note or None)
            if not result.get('success'):
                return ('error', f'❌ {result.get("error", "新增失敗")}', None)
            msg = f'✨ 新增生理期紀錄\n📅 開始日期：{date_str}'
            if note:
                msg += f'\n📝 備註：{note}'
            return ('text', msg, None)

    return ('error', '❌ 無法識別的操作類型。', None)


# ─────────────────────────────────────────────────────────────
# 5. 執行資料查詢
# ─────────────────────────────────────────────────────────────
def execute_query(action, data, user_obj, setting, has_perm_fn):
    """
    依 action 從 DB 讀取資料並回傳。
    回傳 tuple: ('flex'|'text', payload, alt_text) 或 ('error', msg, None)
    """
    from services.flex_message_service import FlexMessageService
    from collections import defaultdict
    import calendar

    # 取得總體範圍（用於標題或單月判斷）
    start_date, end_date, range_label = _get_date_range(data)
    
    # 解析出所有需要查詢的月份
    start_m = int(start_date[5:7])
    end_m = int(end_date[5:7])
    year = int(start_date[:4])
    
    # 如果是跨月查詢（例如 2 到 5 月），我們建立一個卡片列表
    months_to_query = []
    if start_m != end_m:
        curr_m = start_m
        while True:
            months_to_query.append(curr_m)
            if curr_m == end_m: break
            curr_m = curr_m + 1 if curr_m < 12 else 1
    else:
        months_to_query = [start_m]

    # ── 處理記帳查詢 ───────────────────────────────────────────
    if action == 'query_expense':
        if not has_perm_fn('expense'):
            return ('error', '⛔ 此帳號無記帳查看權限，請聯絡帳號擁有者開啟。', None)

        from services.expense_service import ExpenseService
        bubbles = []
        trend_labels = []
        trend_values = []
        
        for m in months_to_query:
            m_year = year if m >= start_m else year + 1
            last_day = calendar.monthrange(m_year, m)[1]
            m_start = f"{m_year}-{m:02d}-01"
            m_end = f"{m_year}-{m:02d}-{last_day}"
            
            summary = ExpenseService().get_summary(m_start, m_end, user=user_obj)
            total = summary.get('total_amount', 0)
            records = summary.get('records', [])
            
            if not records and len(months_to_query) > 1: continue 
            
            trend_labels.append(f"{m}月")
            trend_values.append(total)

            category_stats = defaultdict(lambda: {'count': 0, 'amount': 0, 'emoji': '📦'})
            EMOJI_MAP = {'飲食': '🍔', '交通': '🚌', '娛樂': '🎮', '居住': '🏠', '其他': '📦'}
            for r in records:
                cat_raw = r.get('category', '其他')
                parts = cat_raw.split(' ')
                emoji = parts[0] if len(parts) > 1 and len(parts[0]) <= 3 else EMOJI_MAP.get(cat_raw, '📦')
                cat_name = parts[1] if len(parts) > 1 else cat_raw
                category_stats[cat_name]['count'] += 1
                category_stats[cat_name]['amount'] += int(r['amount'])
                category_stats[cat_name]['emoji'] = emoji

            bubble = FlexMessageService.build_expense_summary_bubble(
                username=user_obj.username,
                start_date=m_start, end_date=m_end,
                total=total, category_stats=category_stats, records=records[:5]
            )
            bubbles.append(bubble)

        if not bubbles:
            return ('text', f'📅 {range_label} 沒有找到任何記帳紀錄喔！', None)
        
        # 如果有多個月份，追加趨勢圖卡片
        if len(bubbles) > 1:
            trend_bubble = FlexMessageService.build_trend_bubble("支出", trend_labels, trend_values, color="#e91e63")
            bubbles.append(trend_bubble)

        if len(bubbles) == 1:
            return ('flex', bubbles[0], f"{range_label}記帳總覽")
        else:
            carousel = {"type": "carousel", "contents": bubbles[:10]}
            return ('flex', carousel, f"{range_label}記帳總覽")

    # ── 處理薪資查詢 ───────────────────────────────────────────
    elif action == 'query_salary':
        if not has_perm_fn('salary'):
            return ('error', '⛔ 此帳號無薪資查看權限，請聯絡帳號擁有者開啟。', None)

        from services.salary_service import SalaryService
        salary_svc = SalaryService()
        bubbles = []
        trend_labels = []
        trend_values = []

        for m in months_to_query:
            m_year = year if m >= start_m else year + 1
            last_day = calendar.monthrange(m_year, m)[1]
            m_start = f"{m_year}-{m:02d}-01"
            m_end = f"{m_year}-{m:02d}-{last_day}"
            
            summary = salary_svc.get_history_summary(m_start, m_end, user=user_obj)
            total_amt = summary.get('total_amount', 0)
            total_hrs = summary.get('total_hours', 0)
            records = summary.get('records', [])

            if not records and len(months_to_query) > 1: continue

            trend_labels.append(f"{m}月")
            trend_values.append(total_amt)

            type_stats = defaultdict(lambda: {'count': 0, 'amount': 0, 'hours': 0})
            for r in records:
                rtype = '排班' if r['type'] == 'shift' else '獎金'
                type_stats[rtype]['count'] += 1
                type_stats[rtype]['amount'] += r.get('amount', 0)
                if r['type'] == 'shift':
                    type_stats[rtype]['hours'] += r.get('hours', 0)

            bubble = FlexMessageService.build_salary_summary_bubble(
                username=user_obj.username,
                start_date=m_start, end_date=m_end,
                total_amt=total_amt, total_hrs=total_hrs,
                type_stats=type_stats, records=records[:5]
            )
            bubbles.append(bubble)

        if not bubbles:
            return ('text', f'📅 {range_label} 沒有找到任何薪資紀錄喔！', None)

        # 如果有多個月份，追加趨勢圖卡片
        if len(bubbles) > 1:
            trend_bubble = FlexMessageService.build_trend_bubble("薪資", trend_labels, trend_values, color="#03a9f4")
            bubbles.append(trend_bubble)

        if len(bubbles) == 1:
            return ('flex', bubbles[0], f"{range_label}薪資總覽")
        else:
            carousel = {"type": "carousel", "contents": bubbles[:10]}
            return ('flex', carousel, f"{range_label}薪資總覽")

    # ── 其他查詢（文字類） ───────────────────────────────────────
    elif action == 'query_period':
        if not has_perm_fn('period'):
            return ('error', '⛔ 此帳號無生理期查看權限，請聯絡帳號擁有者開啟。', None)

        from services.period_service import PeriodService
        period_svc = PeriodService(user_obj.id)
        preds = period_svc.get_predictions(months=2)

        if not preds:
            return ('text', '🩸 目前沒有足夠的歷史紀錄來推算下次生理期，請先記錄至少一次哦！', None)

        p = preds[0]
        now_dt = datetime.utcnow() + timedelta(hours=8)
        next_start = datetime.strptime(p['period_start'], '%Y-%m-%d')
        days_left = (next_start - now_dt.replace(hour=0, minute=0, second=0, microsecond=0)).days

        period_start  = p['period_start'][5:].replace('-', '/')
        days_msg = f'（還有 {days_left} 天）' if days_left > 0 else ('（預計今天）' if days_left == 0 else f'（已過 {abs(days_left)} 天）')

        reply = (
            f'🩸 下次生理期預測\n'
            f'📅 預測開始：{period_start} {days_msg}\n'
            f'🥚 排卵日：{p["ovulation_day"][5:].replace("-", "/")}\n'
            f'💚 易孕期：{p["fertile_window_start"][5:].replace("-", "/")} ～ {p["fertile_window_end"][5:].replace("-", "/")}\n'
            f'📊 平均週期：{period_svc.settings.avg_period_cycle or 28} 天'
        )
        return ('text', reply, None)

    elif action == 'query_balance':
        if not has_perm_fn('expense'):
            return ('error', '⛔ 此帳號無記帳查看權限，請聯絡帳號擁有者開啟。', None)

        from services.expense_service import ExpenseService
        now_dt = datetime.utcnow() + timedelta(hours=8)
        cycle_day = setting.billing_cycle_start_day or 10
        if now_dt.day >= cycle_day:
            cycle_start = now_dt.replace(day=cycle_day)
        else:
            prev_month = (now_dt.replace(day=1) - timedelta(days=1))
            cycle_start = prev_month.replace(day=cycle_day)

        summary = ExpenseService().get_summary(cycle_start.strftime('%Y-%m-%d'), now_dt.strftime('%Y-%m-%d'), user=user_obj)
        spent = summary.get('total_amount', 0)
        budget = setting.monthly_budget or 10000
        remaining = budget - spent
        pct = int(spent / budget * 100) if budget > 0 else 0
        status = '🟢' if pct < 70 else ('🟡' if pct < 90 else '🔴')

        reply = (
            f'💰 本週期預算狀況 {status}\n'
            f'週期：{cycle_start.strftime("%m/%d")} ～ {now_dt.strftime("%m/%d")}\n'
            f'預算：${budget:,.0f}\n'
            f'已支出：${spent:,.0f}（{pct}%）\n'
            f'剩餘：${remaining:,.0f}'
        )
        return ('text', reply, None)

    elif action == 'query_countdown':
        from services.countdown_service import CountdownService
        svc = CountdownService(user_obj.id)
        items = svc.get_all()
        if not items:
            return ('text', '📅 目前沒有設定任何倒數日或紀念日喔！', None)
        
        # 取得即將到來的日子
        upcoming = [i for i in items if not i['is_past'] or i['days_diff'] == 0]
        # Sort by days_diff ascending
        upcoming = sorted(upcoming, key=lambda x: x['days_diff'])
        
        if not upcoming:
            return ('text', '📅 目前沒有即將到來的倒數日或紀念日！', None)
            
        reply_lines = ["✨ 即將到來的日子 ✨"]
        for item in upcoming[:5]:  # 只顯示前 5 筆
            icon = item['icon'] or '📅'
            date_str = item['target_date'][5:].replace('-', '/')
            reply_lines.append(f"{icon} {item['title']}：{item['display_text']} ({date_str})")
            
        return ('text', "\n".join(reply_lines), None)

    return ('error', '❌ 無法執行此查詢。', None)

    return ('error', '❌ 無法執行此查詢。', None)


# ─────────────────────────────────────────────────────────────
# 輔助：時間格式化
# ─────────────────────────────────────────────────────────────
def _fmt_time(t_str):
    """將 '1400' 或 '14.00' 轉換為 '14:00'，並驗證合法性。"""
    import re
    if not t_str:
        return None
    t_str = str(t_str).strip().replace('.', ':')
    if len(t_str) == 4 and t_str.isdigit():
        t_str = f"{t_str[:2]}:{t_str[2:]}"
    if re.match(r'^([01]?\d|2[0-3]):([0-5]\d)$', t_str):
        return t_str
    return None
