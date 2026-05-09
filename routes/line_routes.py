from flask import Blueprint, request, abort, current_app
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from services.line_service import LineService
from models import db, UserSettings, LineBinding, User
import os, json
from datetime import datetime, timedelta

line_bp = Blueprint('line', __name__)

@line_bp.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers.get('X-Line-Signature')

    # get request body as text
    body = request.get_data(as_text=True)
    current_app.logger.info("Request body: " + body)

    handler = LineService.get_handler()
    if not handler:
        return 'Not Configured', 200

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'

# Register Handler Logic separately to avoid circular import issues if possible,
# or just define it here. Since handler is global in LineService, we need to register creates there or use a local one.
# For simplicity in this structure, we'll define a function to register handlers.

def register_line_handlers(handler):
    if not handler: return

    @handler.add(MessageEvent, message=TextMessage)
    def handle_message(event):
        msg = event.message.text.strip()
        user_id = event.source.user_id

        # ── 0. 6 位數字 → 綁定流程（保留原有邏輯）──────────────────────
        if msg.isdigit() and len(msg) == 6:
            setting = UserSettings.query.filter_by(binding_code=msg).first()
            if setting:
                if setting.binding_expiry and setting.binding_expiry > datetime.utcnow():
                    existing = LineBinding.query.filter_by(line_user_id=user_id).first()
                    if existing:
                        LineService.push_message(user_id, "⚠️ 此 LINE 帳號已綁定過其他帳號，請先解除舊的綁定。")
                        return
                    existing_count = LineBinding.query.filter_by(user_id=setting.user_id).count()
                    auto_nickname = f'使用者 {existing_count + 1}'
                    new_binding = LineBinding(
                        user_id=setting.user_id, line_user_id=user_id,
                        nickname=auto_nickname,
                        permissions=json.dumps(["expense", "salary", "period"])
                    )
                    db.session.add(new_binding)
                    setting.line_user_id = user_id
                    setting.binding_code = None
                    setting.binding_expiry = None
                    db.session.commit()
                    LineService.push_message(user_id, "✅ 綁定成功！\n您現在可以接收工具箱的通知報告了，也能透過對話快速記帳！\n輸入「說明」可以看快速記帳教學。")
                else:
                    LineService.push_message(user_id, "❌ 驗證碼已過期，請重新產生。")
            else:
                LineService.push_message(user_id, "❌ 找不到此驗證碼，請確認輸入正確。")
            return

        # ── 1. 說明 / help ───────────────────────────────────────────────
        if msg in ("說明", "help", "Help", "HELP", "指令", "功能"):
            from services.flex_message_service import FlexMessageService
            flex = FlexMessageService.build_help_carousel()
            LineService.push_flex(user_id, "工具箱說明 — 左右滑動查看所有功能", flex)
            return

        # ── 2. 取得綁定資訊 ─────────────────────────────────────────────
        binding = LineBinding.query.filter_by(line_user_id=user_id).first()
        if not binding:
            old_setting = UserSettings.query.filter_by(line_user_id=user_id).first()
            if old_setting:
                binding = LineBinding(
                    user_id=old_setting.user_id, line_user_id=user_id,
                    nickname='本人', permissions=json.dumps(["expense", "salary", "period"])
                )
                db.session.add(binding)
                db.session.commit()

        if not binding:
            LineService.push_message(user_id, "🤖 我是工具箱小幫手。\n請先至系統網站設定頁面產生 6 位數驗證碼，綁定成功後就能用語音或文字快速記帳囉！")
            return

        setting = UserSettings.query.filter_by(user_id=binding.user_id).first()
        user_obj = User.query.get(binding.user_id)

        def has_perm(perm):
            try:
                perms = json.loads(binding.permissions or '[]')
            except Exception:
                perms = []
            return perm in perms

        def get_perms():
            try:
                return json.loads(binding.permissions or '[]')
            except Exception:
                return []

        gemini_key = current_app.config.get('GEMINI_API_KEY')

        # ── 3. 取得或建立對話 session ────────────────────────────────────
        from models import LineConversationSession
        SESSION_TIMEOUT_MINUTES = 30

        session = LineConversationSession.query.filter_by(line_user_id=user_id).first()
        if not session:
            session = LineConversationSession(line_user_id=user_id)
            db.session.add(session)
            db.session.commit()

        # 逾時重置
        if session.updated_at:
            elapsed = (datetime.utcnow() - session.updated_at).total_seconds() / 60
            if elapsed > SESSION_TIMEOUT_MINUTES and session.state != 'IDLE':
                session.state = 'IDLE'
                session.intent = None
                session.collected_data = '{}'
                session.pending_fields = '[]'
                db.session.commit()

        def _reset_session():
            session.state = 'IDLE'
            session.intent = None
            session.collected_data = '{}'
            session.pending_fields = '[]'
            session.updated_at = datetime.utcnow()
            db.session.commit()

        def _save_session(state, intent, collected, pending):
            session.state = state
            session.intent = intent
            session.collected_data = json.dumps(collected, ensure_ascii=False)
            session.pending_fields = json.dumps(pending, ensure_ascii=False)
            session.updated_at = datetime.utcnow()
            db.session.commit()

        def _push_result(result):
            """統一處理 execute_write / execute_query 的回傳結果。"""
            rtype, payload, alt = result
            if rtype == 'error':
                LineService.push_message(user_id, payload)
            elif rtype == 'flex':
                LineService.push_flex(user_id, alt or '工具箱通知', payload)
            else:
                LineService.push_message(user_id, payload)

        # ── 4. 取消指令：清除 session ────────────────────────────────────
        if msg in ("取消", "算了", "不用了", "cancel", "Cancel"):
            if session.state == 'COLLECTING':
                _reset_session()
                LineService.push_message(user_id, "✅ 已取消，隨時可以重新開始！")
            else:
                LineService.push_message(user_id, "💡 目前沒有進行中的操作喔！")
            return

        # ── 5. COLLECTING 狀態：AI 繼續填入欄位 ─────────────────────────
        if session.state == 'COLLECTING' and session.intent:
            intent = session.intent
            try:
                collected = json.loads(session.collected_data or '{}')
                pending   = json.loads(session.pending_fields or '[]')
            except Exception:
                collected, pending = {}, []

            if gemini_key and len(msg) < 300:
                from services.ai_chat_service import analyze_intent, get_missing_fields, build_question, execute_write
                ai_result = analyze_intent(msg, collected, get_perms(), gemini_key)

                # 取消意圖
                if ai_result.get('action') == 'cancel':
                    _reset_session()
                    LineService.push_message(user_id, "✅ 已取消，隨時可以重新開始！")
                    return

                # 合併新提取的欄位到 collected
                new_data = ai_result.get('data', {})
                collected.update({k: v for k, v in new_data.items() if v is not None and v != ''})
            else:
                # 無 AI key：把整段訊息塞進第一個 pending 欄位
                if pending:
                    collected[pending[0]] = msg

            # 重新計算缺少欄位
            from services.ai_chat_service import get_missing_fields, build_question, execute_write
            still_missing = get_missing_fields(intent, collected)

            if still_missing:
                _save_session('COLLECTING', intent, collected, still_missing)
                LineService.push_message(user_id, build_question(still_missing[0]))
            else:
                # 資料齊全，執行寫入
                _reset_session()
                result = execute_write(intent, collected, user_obj, setting, has_perm)
                _push_result(result)
            return

        # ── 6. IDLE 狀態：先試固定指令快速通道 ──────────────────────────
        now_dt = datetime.utcnow() + timedelta(hours=8)

        def parse_date(d_str, default_dt):
            if not d_str:
                return default_dt
            current_year = default_dt.year
            import re as _re
            enriched = f"{current_year}/{d_str}" if _re.match(r'^\d{1,2}/\d{1,2}$', d_str) else d_str
            formats = [
                ("%Y/%m/%d/%H:%M", True, True, True), ("%Y/%m/%d", True, True, False),
                ("%m/%d/%H:%M", False, True, True),   ("%H:%M", False, False, True),
                ("%H%M", False, False, True),
            ]
            for fmt, has_year, has_date, has_time in formats:
                try:
                    pd_ = datetime.strptime(enriched if has_date else d_str, fmt)
                    res = default_dt
                    if has_year:  res = res.replace(year=pd_.year)
                    if has_date:  res = res.replace(month=pd_.month, day=pd_.day)
                    if has_time:  res = res.replace(hour=pd_.hour, minute=pd_.minute, second=0)
                    else:         res = res.replace(hour=12, minute=0, second=0)
                    return res
                except ValueError:
                    pass
            return default_dt

        def get_query_month_range(month_str):
            import re, calendar
            now = datetime.utcnow() + timedelta(hours=8)
            year, month = now.year, now.month
            if month_str:
                match = re.search(r'(\d+)', month_str)
                if match:
                    parsed_month = int(match.group(1))
                    if 1 <= parsed_month <= 12:
                        month = parsed_month
                        if month > now.month:
                            year -= 1
            last_day = calendar.monthrange(year, month)[1]
            return f"{year}-{month:02d}-01", f"{year}-{month:02d}-{last_day}"

        handled = False

        # 6a. 查詢記帳 / 查詢薪水（固定格式快速通道）
        if msg.startswith("查詢記帳") or msg.startswith("查詢薪水") or msg.startswith("查詢薪資"):
            parts = msg.split()
            month_str = parts[1] if len(parts) > 1 else None
            start_date, end_date = get_query_month_range(month_str)
            if msg.startswith("查詢記帳"):
                if not has_perm("expense"):
                    LineService.push_message(user_id, "⛔ 此帳號無記帳權限，請聯絡帳號擁有者開啟。")
                    return
                from services.ai_chat_service import execute_query
                result = execute_query('query_expense', {'month': int(start_date[5:7])}, user_obj, setting, has_perm)
            else:
                if not has_perm("salary"):
                    LineService.push_message(user_id, "⛔ 此帳號無薪資管理權限，請聯絡帳號擁有者開啟。")
                    return
                from services.ai_chat_service import execute_query
                result = execute_query('query_salary', {'month': int(start_date[5:7])}, user_obj, setting, has_perm)
            _push_result(result)
            return

        # 6b. 記帳（固定格式快速通道）
        if msg.startswith("記帳"):
            if not has_perm("expense"):
                LineService.push_message(user_id, "⛔ 此帳號無記帳權限，請聯絡帳號擁有者開啟。")
                return
            if msg.strip() == "記帳":
                LineService.push_message(user_id, "✏️ 準備記帳了嗎？請直接輸入您花費的項目與金額：\n\n👉 例如：記帳 午餐 150\n👉 例如：記帳 咖啡 飲食 65\n\n💡 或者直接口語說，AI 會幫你自動記錄！")
                return
            parts = [p for p in msg.split() if p.strip()][1:]
            amount, date_str, text_parts = None, None, []
            for p in parts:
                if amount is None:
                    try:
                        val = float(p)
                        if val > 0: amount = val; continue
                    except ValueError: pass
                if date_str is None and ('/' in p or ':' in p or (len(p)==4 and p.isdigit())):
                    date_str = p.replace('.', ':'); continue
                text_parts.append(p)
            if amount is None:
                LineService.push_message(user_id, "❌ 找不到金額！\n例如：記帳 午餐 150")
                return
            name     = text_parts[0] if text_parts else "隨手記"
            category = text_parts[1] if len(text_parts) > 1 else "飲食"
            final_dt = parse_date(date_str, now_dt)
            now_str  = final_dt.strftime('%Y-%m-%d %H:%M:%S')
            from models import ExpenseRecord
            db.session.add(ExpenseRecord(user_id=setting.user_id, timestamp=now_str, category=category, amount=amount, note=name))
            db.session.commit()
            from services.flex_message_service import FlexMessageService
            flex = FlexMessageService.build_expense_confirm(name=name, amount=amount, category=category, timestamp=now_str)
            LineService.push_flex(user_id, f"支出記錄成功：{name} ${amount:g}", flex)
            return

        # 6c. 獎金（固定格式快速通道）
        if msg.startswith("獎金"):
            if not has_perm("salary"):
                LineService.push_message(user_id, "⛔ 此帳號無薪資管理權限，請聯絡帳號擁有者開啟。")
                return
            parts = [p for p in msg.split() if p.strip()][1:]
            amounts, text_parts, date_str = [], [], None
            for p in parts:
                if date_str is None and '/' in p: date_str = p; continue
                try: amounts.append(float(p))
                except ValueError: text_parts.append(p)
            if not amounts or amounts[0] <= 0:
                LineService.push_message(user_id, "❌ 找不到金額！例如：獎金 1500 三節")
                return
            amount   = int(amounts[0])
            hours    = amounts[1] if len(amounts) > 1 else 0.0
            note     = " ".join(text_parts)
            final_dt = parse_date(date_str, now_dt)
            now_date = final_dt.strftime('%Y-%m-%d')
            from models import SalaryRecord
            db.session.add(SalaryRecord(user_id=setting.user_id, date=now_date, type='bonus', amount=amount, hours=hours, note=note))
            db.session.commit()
            from services.flex_message_service import FlexMessageService
            flex = FlexMessageService.build_salary_confirm(record_type='bonus', date=now_date, amount=amount, hours=hours, note=note)
            LineService.push_flex(user_id, f"獎金記錄成功：${amount:,}", flex)
            return

        # 6d. 排班（固定格式快速通道）
        if msg.startswith("排班") or msg.startswith("打工"):
            if not has_perm("salary"):
                LineService.push_message(user_id, "⛔ 此帳號無薪資管理權限，請聯絡帳號擁有者開啟。")
                return
            parts = [p for p in msg.split() if p.strip()][1:]
            times, amounts, text_parts, date_str = [], [], [], None
            for p in parts:
                if date_str is None and '/' in p: date_str = p; continue
                if ':' in p or '.' in p or (len(p)==4 and p.isdigit()): times.append(p)
                else:
                    try: amounts.append(float(p))
                    except ValueError: text_parts.append(p)
            start_str = times[0] if times else "12:00"
            end_str   = times[1] if len(times) > 1 else "18:00"
            import re
            def fmt(t):
                if len(t)==4 and t.isdigit(): t = f"{t[:2]}:{t[2:]}"
                t = t.replace('.', ':')
                return t if re.match(r'^([01]?\d|2[0-3]):([0-5]\d)$', t) else None
            start_time = fmt(start_str)
            end_time   = fmt(end_str)
            if not (start_time and end_time):
                LineService.push_message(user_id, "❌ 時間格式錯誤！請使用 18:00 或 1800。")
                return
            t1 = datetime.strptime(start_time, "%H:%M")
            t2 = datetime.strptime(end_time,   "%H:%M")
            if t2 < t1: t2 += timedelta(days=1)
            hours = (t2 - t1).total_seconds() / 3600.0
            custom_rate = amounts[0] if amounts else None
            note        = " ".join(text_parts)
            rate        = custom_rate if custom_rate is not None else float(setting.hourly_rate or 196.0)
            final_dt    = parse_date(date_str, now_dt)
            now_date    = final_dt.strftime('%Y-%m-%d')
            from services.salary_service import _apply_holiday_pay
            effective_rate, amount, updated_note = _apply_holiday_pay(now_date, rate, hours, note)
            from models import SalaryRecord
            db.session.add(SalaryRecord(user_id=setting.user_id, date=now_date, type='shift',
                start_time=start_time, end_time=end_time, hours=hours, rate=effective_rate, amount=amount, note=updated_note))
            db.session.commit()
            from services.flex_message_service import FlexMessageService
            flex = FlexMessageService.build_salary_confirm(record_type='shift', date=now_date, amount=amount, hours=hours, start_time=start_time, end_time=end_time, note=updated_note)
            LineService.push_flex(user_id, f"排班記錄成功：{now_date} {start_time}~{end_time}", flex)
            return

        # 6e. 月經（固定格式快速通道）
        if msg.startswith("月經") or msg.startswith("生理期") or msg.lower().startswith("mc"):
            if not has_perm("period"):
                LineService.push_message(user_id, "⛔ 此帳號無生理期記錄權限，請聯絡帳號擁有者開啟。")
                return
            parts = [p for p in msg.split() if p.strip()][1:]
            dates = [p for p in parts if '/' in p]
            text_parts = [p for p in parts if '/' not in p]
            note = " ".join(text_parts).strip()
            from services.period_service import PeriodService
            period_svc = PeriodService(setting.user_id)
            history    = period_svc.get_history()
            latest     = history[0] if history else None
            if "結束" in note:
                if not latest or latest['end_date']:
                    LineService.push_message(user_id, "❌ 目前沒有進行中的生理期可以結束喔！")
                    return
                end_dt = parse_date(dates[0] if dates else None, now_dt)
                period_svc.update_record(latest['id'], start_date=latest['start_date'], end_date=end_dt.strftime('%Y-%m-%d'), note=latest['note'])
                LineService.push_message(user_id, f"🩸 結束生理期紀錄\n📅 開始：{latest['start_date'][5:].replace('-', '/')}\n📅 結束：{end_dt.strftime('%m/%d')}")
                return
            start_dt = parse_date(dates[0] if dates else None, now_dt)
            end_dt2  = parse_date(dates[1], now_dt) if len(dates) > 1 else None
            result   = period_svc.add_record(start_date=start_dt.strftime('%Y-%m-%d'), end_date=end_dt2.strftime('%Y-%m-%d') if end_dt2 else None, note=note or None)
            if not result.get("success"):
                LineService.push_message(user_id, f"❌ {result.get('error', '新增失敗')}")
                return
            reply = f"🩸 新增生理期紀錄\n📅 開始：{start_dt.strftime('%m/%d')}"
            if end_dt2: reply += f"\n📅 結束：{end_dt2.strftime('%m/%d')}"
            if note:    reply += f"\n📝 備註：{note}"
            LineService.push_message(user_id, reply)
            return

        # 6f. 查詢 LINE ID
        if msg == "查詢":
            LineService.push_message(user_id, f"您的 LINE User ID: {user_id}")
            return

        # ── 7. AI 意圖分析（IDLE fallback）──────────────────────────────
        if not gemini_key or len(msg) >= 300:
            from services.flex_message_service import FlexMessageService
            LineService.push_flex(user_id, "工具箱說明 — 左右滑動查看所有功能", FlexMessageService.build_help_carousel())
            return

        from services.ai_chat_service import (
            analyze_intent, get_missing_fields, build_question,
            execute_write, execute_query
        )

        try:
            ai_result = analyze_intent(msg, {}, get_perms(), gemini_key)
        except Exception as e:
            current_app.logger.error(f"[line_routes] AI 分析例外: {e}")
            from services.flex_message_service import FlexMessageService
            LineService.push_flex(user_id, "工具箱說明", FlexMessageService.build_help_carousel())
            return

        action = ai_result.get('action', 'unknown')
        data   = ai_result.get('data', {})

        # 7a. 查詢類 intent：直接讀取 DB 回傳
        if action in ('query_expense', 'query_salary', 'query_period', 'query_balance', 'query_countdown'):
            result = execute_query(action, data, user_obj, setting, has_perm)
            _push_result(result)
            return

        # 7b. 取消
        if action == 'cancel':
            LineService.push_message(user_id, "💡 目前沒有進行中的操作喔！")
            return

        # 7c. 寫入類 intent
        if action in ('expense', 'shift', 'bonus', 'period'):
            missing = get_missing_fields(action, data)
            if not missing:
                # 資料齊全，直接寫入
                result = execute_write(action, data, user_obj, setting, has_perm)
                _push_result(result)
            else:
                # 資料不足，建立 session 開始追問
                _save_session('COLLECTING', action, data, missing)
                # 先回覆確認意圖 + 問第一個欄位
                intent_names = {'expense': '記帳', 'shift': '排班', 'bonus': '獎金', 'period': '生理期'}
                LineService.push_message(user_id, f"好的，我來幫你記錄{intent_names.get(action, '')}！\n{build_question(missing[0])}")
            return

        # 7d. chat 自然語言回覆
        if action == 'chat':
            reply = ai_result.get('reply', '這個我還不太懂，你可以直接輸入「說明」查看我能做什麼喔！')
            LineService.push_message(user_id, reply)
            return

        # 7e. unknown → 說明 Carousel
        from services.flex_message_service import FlexMessageService
        LineService.push_flex(user_id, "工具箱說明 — 左右滑動查看所有功能", FlexMessageService.build_help_carousel())

# Hacky way to register handlers on import or first request?
# Better: In app factory, call a setup function.


