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
                ai_result = analyze_intent(msg, collected, get_perms(), gemini_key, current_intent=intent)

                action = ai_result.get('action', 'unknown').lower()
                if action == 'error':
                    from services.ai_chat_service import fallback_extract
                    ai_result = fallback_extract(intent, msg, collected)
                    action = ai_result.get('action', 'unknown').lower()

                # 取消意圖
                if action == 'cancel':
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

        # ── 6. IDLE：只保留兩個無需 AI 的固定指令快速通道 ──────────────
        # 6a. 查詢記帳 / 查詢薪水（固定格式，不需要 AI）
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

        # 6b. 查詢類快速通道：預算 / 生理期 / 倒數 / 紀念日（零 token）
        QUERY_SHORTCUTS = {
            '查詢預算':   'query_balance',
            '查詢生理期': 'query_period',
            '查詢倒數':   'query_countdown',
            '查詢紀念日': 'query_anniversary',
        }
        if msg in QUERY_SHORTCUTS:
            from services.ai_chat_service import execute_query
            result = execute_query(QUERY_SHORTCUTS[msg], {}, user_obj, setting, has_perm)
            _push_result(result)
            return

        # 6c. 快速記帳：記帳 <金額> <項目> [類別]
        import re as _re
        _time_re = _re.compile(r'^([01]?\d|2[0-3]):([0-5]\d)$')

        if msg.startswith('記帳 '):
            parts = msg.split()
            _expense_fmt = '❌ 格式錯誤！\n正確格式：記帳 <金額> <項目> [類別]\n\n範例：\n記帳 85 午餐\n記帳 120 咖啡 飲食'
            if len(parts) >= 2:
                try:
                    amount = float(parts[1])
                    if amount <= 0:
                        raise ValueError
                    name = parts[2] if len(parts) >= 3 else None
                    category = parts[3] if len(parts) >= 4 else '飲食'
                    if not name:
                        if not has_perm('expense'):
                            LineService.push_message(user_id, '⛔ 此帳號無記帳權限，請聯絡帳號擁有者開啟。')
                            return
                        from services.ai_chat_service import build_question
                        _save_session('COLLECTING', 'expense',
                                      {'amount': amount, 'category': category}, ['name'])
                        LineService.push_message(user_id,
                            f'⚠️ 記帳項目名稱是必填的！\n\n{build_question("name")}')
                    else:
                        from services.ai_chat_service import execute_write
                        result = execute_write('expense',
                            {'amount': amount, 'name': name, 'category': category},
                            user_obj, setting, has_perm)
                        _push_result(result)
                except ValueError:
                    LineService.push_message(user_id, _expense_fmt)
            else:
                LineService.push_message(user_id, _expense_fmt)
            return

        # 6d. 快速排班：排班 <開始> <結束> [YYYY-MM-DD]
        if msg.startswith('排班 '):
            def _parse_shift_time(s):
                s = s.strip().replace('.', ':')
                if len(s) == 4 and s.isdigit():
                    s = f'{s[:2]}:{s[2:]}'
                return s if _time_re.match(s) else None

            parts = msg.split()
            times, date_str = [], None
            for p in parts[1:]:
                if _re.match(r'^\d{4}-\d{2}-\d{2}$', p):
                    date_str = p
                else:
                    t = _parse_shift_time(p)
                    if t:
                        times.append(t)

            if len(times) >= 2:
                from services.ai_chat_service import execute_write
                data = {'start_time': times[0], 'end_time': times[1]}
                if date_str:
                    data['date'] = date_str
                result = execute_write('shift', data, user_obj, setting, has_perm)
                _push_result(result)
            else:
                LineService.push_message(user_id,
                    '❌ 格式錯誤！\n正確格式：排班 <開始> <結束> [日期]\n\n範例：\n排班 14:00 21:00\n排班 1400 2100 2026-05-15')
            return

        # 6e. 快速獎金：獎金 <金額> [備註]
        if msg.startswith('獎金 '):
            parts = msg.split(maxsplit=2)
            try:
                amount = float(parts[1])
                if amount <= 0:
                    raise ValueError
                note = parts[2] if len(parts) >= 3 else ''
                from services.ai_chat_service import execute_write
                result = execute_write('bonus', {'amount': amount, 'note': note},
                                       user_obj, setting, has_perm)
                _push_result(result)
            except (ValueError, IndexError):
                LineService.push_message(user_id,
                    '❌ 格式錯誤！\n正確格式：獎金 <金額> [備註]\n\n範例：\n獎金 500\n獎金 1000 全勤獎金')
            return

        # 6f. 快速生理期：精確比對關鍵字
        if msg in ('生理期開始', '月經來了', '月經開始'):
            from services.ai_chat_service import execute_write
            result = execute_write('period', {'type': 'start'}, user_obj, setting, has_perm)
            _push_result(result)
            return
        if msg in ('生理期結束', '月經結束'):
            from services.ai_chat_service import execute_write
            result = execute_write('period', {'type': 'end'}, user_obj, setting, has_perm)
            _push_result(result)
            return

        # 6g. 查詢 LINE ID（特殊指令，不需要 AI）
        if msg.strip() == "查詢":
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
            LineService.push_message(user_id, "❌ 系統發生預期外的錯誤，請稍後再試。")
            return

        action = ai_result.get('action', 'unknown').lower()
        data   = ai_result.get('data', {})

        if action == 'error':
            LineService.push_message(user_id, ai_result.get('reply', '❌ AI 發生錯誤，請稍後再試。'))
            return

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
        if action in ('expense', 'shift', 'bonus', 'period', 'countdown'):
            missing = get_missing_fields(action, data)
            if not missing:
                # 資料齊全，直接寫入
                result = execute_write(action, data, user_obj, setting, has_perm)
                _push_result(result)
            else:
                # 資料不足，建立 session 開始追問
                _save_session('COLLECTING', action, data, missing)
                # 先回覆確認意圖 + 問第一個欄位
                intent_names = {'expense': '記帳', 'shift': '排班', 'bonus': '獎金', 'period': '生理期', 'countdown': '倒數/紀念日'}
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


