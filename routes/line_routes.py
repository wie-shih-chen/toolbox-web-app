from flask import Blueprint, request, abort, current_app
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, ImageMessage, PostbackEvent
from services.line_service import LineService
from models import db, UserSettings, LineBinding, User
import os, json
from datetime import datetime, timedelta

line_bp = Blueprint('line', __name__)

@line_bp.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)
    current_app.logger.info("Request body: " + body)

    handler = LineService.get_handler()
    if not handler:
        return 'Not Configured', 200

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'


def get_quick_replies(intent=None):
    from linebot.models import QuickReply, QuickReplyButton, MessageAction
    items = []
    if intent in ('expense', 'query_expense'):
        items = [
            QuickReplyButton(action=MessageAction(label="💰 繼續記帳", text="記帳")),
            QuickReplyButton(action=MessageAction(label="📊 查詢本月收支", text="查詢記帳")),
        ]
    elif intent in ('shift', 'query_salary'):
        items = [
            QuickReplyButton(action=MessageAction(label="🕒 繼續排班", text="排班")),
            QuickReplyButton(action=MessageAction(label="💵 查詢本月薪水", text="查詢薪水")),
        ]
    else:
        items = [
            QuickReplyButton(action=MessageAction(label="💰 記帳", text="記帳 ")),
            QuickReplyButton(action=MessageAction(label="🕒 排班", text="排班 ")),
            QuickReplyButton(action=MessageAction(label="❓ 說明", text="說明")),
        ]
    return QuickReply(items=items)


# ─────────────────────────────────────────────────────────────
# 內嵌的 execute_write（不依賴 ai_chat_service）
# ─────────────────────────────────────────────────────────────
def _execute_write(intent, data, user_obj, setting, has_perm_fn):
    """執行資料寫入，回傳 ('flex'|'text'|'error', payload, alt_text)。"""
    from services.flex_message_service import FlexMessageService
    now_dt = datetime.utcnow() + timedelta(hours=8)

    if intent == 'expense':
        if not has_perm_fn('expense'):
            return ('error', '⛔ 此帳號無記帳權限，請聯絡帳號擁有者開啟。', None)
        name     = data.get('name', '隨手記')
        amount   = float(data.get('amount', 0))
        category = data.get('category', '飲食')
        date_str = data.get('date', now_dt.strftime('%Y-%m-%d'))
        record_time = f"{date_str} {now_dt.strftime('%H:%M:%S')}"
        from models import ExpenseRecord
        rec = ExpenseRecord(user_id=user_obj.id, timestamp=record_time,
                            category=category, amount=amount, note=name)
        db.session.add(rec)
        db.session.commit()
        flex = FlexMessageService.build_expense_confirm(
            name=name, amount=amount, category=category, timestamp=record_time, ai=False)
        return ('flex', flex, f'記帳：{name} ${amount:g}')

    elif intent == 'shift':
        if not has_perm_fn('salary'):
            return ('error', '⛔ 此帳號無薪資管理權限，請聯絡帳號擁有者開啟。', None)
        import re
        def fmt(t):
            if not t: return None
            t = str(t).strip().replace('.', ':')
            if len(t) == 4 and t.isdigit(): t = f"{t[:2]}:{t[2:]}"
            return t if re.match(r'^([01]?\d|2[0-3]):([0-5]\d)$', t) else None
        start_time = fmt(data.get('start_time', '09:00'))
        end_time   = fmt(data.get('end_time', '18:00'))
        if not (start_time and end_time):
            return ('error', '❌ 時間格式有誤，請重新輸入（例如：14:00）', None)
        date_str = data.get('date', now_dt.strftime('%Y-%m-%d'))
        note = data.get('note', '')
        t1 = datetime.strptime(start_time, '%H:%M')
        t2 = datetime.strptime(end_time, '%H:%M')
        if t2 < t1: t2 += timedelta(days=1)
        hours = (t2 - t1).total_seconds() / 3600.0
        rate = float(setting.hourly_rate or 196.0)
        from services.salary_service import _apply_holiday_pay
        effective_rate, amount, updated_note = _apply_holiday_pay(date_str, rate, hours, note)
        from models import SalaryRecord
        rec = SalaryRecord(user_id=user_obj.id, date=date_str, type='shift',
                           start_time=start_time, end_time=end_time,
                           hours=hours, rate=effective_rate, amount=amount, note=updated_note)
        db.session.add(rec)
        db.session.commit()
        flex = FlexMessageService.build_salary_confirm(
            record_type='shift', date=date_str, amount=amount, hours=hours,
            start_time=start_time, end_time=end_time, note=updated_note, ai=False)
        return ('flex', flex, f'排班：{date_str} {start_time}~{end_time}')

    elif intent == 'bonus':
        if not has_perm_fn('salary'):
            return ('error', '⛔ 此帳號無薪資管理權限，請聯絡帳號擁有者開啟。', None)
        amount = int(float(data.get('amount', 0)))
        date_str = data.get('date', now_dt.strftime('%Y-%m-%d'))
        note = data.get('note', '')
        from models import SalaryRecord
        rec = SalaryRecord(user_id=user_obj.id, date=date_str, type='bonus',
                           amount=amount, hours=0, note=note)
        db.session.add(rec)
        db.session.commit()
        flex = FlexMessageService.build_salary_confirm(
            record_type='bonus', date=date_str, amount=amount, note=note, ai=False)
        return ('flex', flex, f'獎金：${amount:,}')

    elif intent == 'period':
        if not has_perm_fn('period'):
            return ('error', '⛔ 此帳號無生理期紀錄權限，請聯絡帳號擁有者開啟。', None)
        ptype    = data.get('type', 'start')
        date_str = data.get('date', now_dt.strftime('%Y-%m-%d'))
        note     = data.get('note', '')
        from services.period_service import PeriodService
        svc = PeriodService(user_obj.id)
        if ptype == 'end':
            history = svc.get_history()
            latest = history[0] if history else None
            if not latest or latest['end_date']:
                return ('error', '❌ 目前沒有進行中的生理期可以結束喔！', None)
            svc.update_record(latest['id'], start_date=latest['start_date'],
                              end_date=date_str, note=latest['note'])
            msg = f'✨ 生理期結束紀錄\n📅 結束日期：{date_str}'
        else:
            result = svc.add_record(start_date=date_str, end_date=None, note=note or None)
            if not result.get('success'):
                return ('error', f'❌ {result.get("error", "新增失敗")}', None)
            msg = f'✨ 新增生理期紀錄\n📅 開始日期：{date_str}'
        if note: msg += f'\n📝 備註：{note}'
        return ('text', msg, None)

    return ('error', '❌ 無法識別的操作類型。', None)


# ─────────────────────────────────────────────────────────────
# 內嵌的 execute_query（不依賴 ai_chat_service）
# ─────────────────────────────────────────────────────────────
def _execute_query(action, data, user_obj, setting, has_perm_fn):
    """執行資料查詢，回傳 ('flex'|'text'|'error', payload, alt_text)。"""
    from services.flex_message_service import FlexMessageService
    from collections import defaultdict
    import calendar
    from datetime import datetime, timedelta

    now_dt = datetime.utcnow() + timedelta(hours=8)
    month  = data.get('month', now_dt.month)
    year   = data.get('year', now_dt.year)
    try:
        month = int(month)
        year  = int(year)
    except Exception:
        month = now_dt.month
        year  = now_dt.year

    last_day  = calendar.monthrange(year, month)[1]
    start_date = f"{year}-{month:02d}-01"
    end_date   = f"{year}-{month:02d}-{last_day}"
    label      = f"{month}月"

    if action == 'query_expense':
        if not has_perm_fn('expense'):
            return ('error', '⛔ 此帳號無記帳查看權限，請聯絡帳號擁有者開啟。', None)
        from services.expense_service import ExpenseService
        summary  = ExpenseService().get_summary(start_date, end_date, user=user_obj)
        total    = summary.get('total_amount', 0)
        records  = summary.get('records', [])
        EMOJI_MAP = {'飲食': '🍔', '交通': '🚌', '娛樂': '🎮', '居住': '🏠', '其他': '📦'}
        cat_stats = defaultdict(lambda: {'count': 0, 'amount': 0, 'emoji': '📦'})
        for r in records:
            cat_raw = r.get('category', '其他')
            parts = cat_raw.split(' ')
            emoji = parts[0] if len(parts) > 1 and len(parts[0]) <= 3 else EMOJI_MAP.get(cat_raw, '📦')
            cat_name = parts[1] if len(parts) > 1 else cat_raw
            cat_stats[cat_name]['count'] += 1
            cat_stats[cat_name]['amount'] += int(r['amount'])
            cat_stats[cat_name]['emoji'] = emoji
        if not records:
            return ('text', f'📅 {label} 沒有找到任何記帳紀錄喔！', None)
        bubble = FlexMessageService.build_expense_summary_bubble(
            username=user_obj.username, start_date=start_date, end_date=end_date,
            total=total, category_stats=cat_stats, records=records[:10])
        return ('flex', bubble, f'{label}記帳總覽')

    elif action == 'query_salary':
        if not has_perm_fn('salary'):
            return ('error', '⛔ 此帳號無薪資查看權限，請聯絡帳號擁有者開啟。', None)
        from services.salary_service import SalaryService
        svc     = SalaryService()
        summary = svc.get_history_summary(start_date, end_date, user=user_obj)
        total_amt = summary.get('total_amount', 0)
        total_hrs = summary.get('total_hours', 0)
        records   = summary.get('records', [])
        type_stats = defaultdict(lambda: {'count': 0, 'amount': 0, 'hours': 0})
        for r in records:
            rtype = '排班' if r['type'] == 'shift' else '獎金'
            type_stats[rtype]['count']  += 1
            type_stats[rtype]['amount'] += r.get('amount', 0)
            if r['type'] == 'shift':
                type_stats[rtype]['hours'] += r.get('hours', 0)
        if not records:
            return ('text', f'📅 {label} 沒有找到任何薪資紀錄喔！', None)
        bubble = FlexMessageService.build_salary_summary_bubble(
            username=user_obj.username, start_date=start_date, end_date=end_date,
            total_amt=total_amt, total_hrs=total_hrs,
            type_stats=type_stats, records=records[:10])
        return ('flex', bubble, f'{label}薪資總覽')

    elif action == 'query_period':
        if not has_perm_fn('period'):
            return ('error', '⛔ 此帳號無生理期查看權限，請聯絡帳號擁有者開啟。', None)
        from services.period_service import PeriodService
        svc   = PeriodService(user_obj.id)
        preds = svc.get_predictions(months=2)
        if not preds:
            return ('text', '🩸 目前沒有足夠的歷史紀錄來推算，請先記錄至少一次哦！', None)
        p = preds[0]
        next_start = datetime.strptime(p['period_start'], '%Y-%m-%d')
        days_left  = (next_start - now_dt.replace(hour=0, minute=0, second=0, microsecond=0)).days
        days_msg   = f'（還有 {days_left} 天）' if days_left > 0 else ('（預計今天）' if days_left == 0 else f'（已過 {abs(days_left)} 天）')
        reply = (
            f'🩸 下次生理期預測\n'
            f'📅 預測開始：{p["period_start"][5:].replace("-", "/")} {days_msg}\n'
            f'🥚 排卵日：{p["ovulation_day"][5:].replace("-", "/")}\n'
            f'💚 易孕期：{p["fertile_window_start"][5:].replace("-", "/")} ～ {p["fertile_window_end"][5:].replace("-", "/")}\n'
            f'📊 平均週期：{svc.settings.avg_period_cycle or 28} 天'
        )
        return ('text', reply, None)

    elif action == 'query_balance':
        if not has_perm_fn('expense'):
            return ('error', '⛔ 此帳號無記帳查看權限，請聯絡帳號擁有者開啟。', None)
        from services.expense_service import ExpenseService
        cycle_day = setting.billing_cycle_start_day or 10
        if now_dt.day >= cycle_day:
            cycle_start = now_dt.replace(day=cycle_day)
        else:
            prev = (now_dt.replace(day=1) - timedelta(days=1))
            cycle_start = prev.replace(day=cycle_day)
        summary   = ExpenseService().get_summary(cycle_start.strftime('%Y-%m-%d'), now_dt.strftime('%Y-%m-%d'), user=user_obj)
        spent     = summary.get('total_amount', 0)
        budget    = setting.monthly_budget or 10000
        remaining = budget - spent
        pct       = int(spent / budget * 100) if budget > 0 else 0
        status    = '🟢' if pct < 70 else ('🟡' if pct < 90 else '🔴')
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
        upcoming = sorted([i for i in svc.get_all() if not i['is_past'] or i['days_diff'] == 0],
                          key=lambda x: x['days_diff'])
        if not upcoming:
            return ('text', '📅 目前沒有即將到來的倒數日或紀念日！', None)
        lines = ['✨ 即將到來的日子 ✨']
        for item in upcoming[:5]:
            icon = item['icon'] or '📅'
            date = item['target_date'][5:].replace('-', '/')
            lines.append(f"{icon} {item['title']}：{item['display_text']} ({date})")
        return ('text', '\n'.join(lines), None)

    return ('error', '❌ 無法執行此查詢。', None)


def register_line_handlers(handler):
    if not handler: return

    @handler.add(MessageEvent, message=TextMessage)
    def handle_message(event):
        msg     = event.message.text.strip()
        user_id = event.source.user_id
        token   = getattr(event, 'reply_token', None)

        def reply(text, qr=None):
            LineService.push_message(user_id, text, quick_reply=qr, reply_token=token)

        def reply_flex(alt, contents, qr=None):
            LineService.push_flex(user_id, alt, contents, quick_reply=qr, reply_token=token)

        def push_result(result, intent=None):
            rtype, payload, alt = result
            qr = get_quick_replies(intent)
            if rtype == 'error':
                reply(payload, qr)
            elif rtype == 'flex':
                reply_flex(alt or '工具箱通知', payload, qr)
            else:
                reply(payload, qr)

        # ── 0. 6 位數字綁定流程 ──────────────────────────────────────
        if msg.isdigit() and len(msg) == 6:
            setting = UserSettings.query.filter_by(binding_code=msg).first()
            if setting:
                if setting.binding_expiry and setting.binding_expiry > datetime.utcnow():
                    existing = LineBinding.query.filter_by(line_user_id=user_id).first()
                    if existing:
                        reply("⚠️ 此 LINE 帳號已綁定過其他帳號，請先解除舊的綁定。")
                        return
                    count = LineBinding.query.filter_by(user_id=setting.user_id).count()
                    new_binding = LineBinding(
                        user_id=setting.user_id, line_user_id=user_id,
                        nickname=f'使用者 {count + 1}',
                        permissions=json.dumps(["expense", "salary", "period"])
                    )
                    db.session.add(new_binding)
                    setting.line_user_id = user_id
                    setting.binding_code = None
                    setting.binding_expiry = None
                    db.session.commit()
                    reply("✅ 綁定成功！\n您現在可以透過對話快速記帳了！\n輸入「說明」查看所有指令。")
                else:
                    reply("❌ 驗證碼已過期，請重新產生。")
            else:
                reply("❌ 找不到此驗證碼，請確認輸入正確。")
            return

        # ── 1. 說明 ─────────────────────────────────────────────────
        if msg in ("說明", "help", "Help", "HELP", "指令", "功能"):
            from services.flex_message_service import FlexMessageService
            reply_flex("工具箱說明 — 左右滑動查看所有功能", FlexMessageService.build_help_carousel())
            return

        # ── 2. 取得綁定資訊 ─────────────────────────────────────────
        binding = LineBinding.query.filter_by(line_user_id=user_id).first()
        if not binding:
            old = UserSettings.query.filter_by(line_user_id=user_id).first()
            if old:
                binding = LineBinding(
                    user_id=old.user_id, line_user_id=user_id,
                    nickname='本人', permissions=json.dumps(["expense", "salary", "period"])
                )
                db.session.add(binding)
                db.session.commit()

        if not binding:
            reply("🤖 我是工具箱小幫手。\n請先至系統網站設定頁面產生 6 位數驗證碼，綁定成功後就能快速記帳囉！")
            return

        setting  = UserSettings.query.filter_by(user_id=binding.user_id).first()
        user_obj = User.query.get(binding.user_id)

        def has_perm(perm):
            try: return perm in json.loads(binding.permissions or '[]')
            except: return False

        # ── 3. 查詢指令（固定格式，無需 AI）────────────────────────
        def get_query_month(part=None):
            import re, calendar
            now = datetime.utcnow() + timedelta(hours=8)
            y, m = now.year, now.month
            if part:
                match = re.search(r'(\d+)', part)
                if match:
                    parsed = int(match.group(1))
                    if 1 <= parsed <= 12:
                        m = parsed
                        if m > now.month: y -= 1
            return {'month': m, 'year': y}

        if msg.startswith("查詢記帳") or msg.startswith("查詢薪水") or msg.startswith("查詢薪資"):
            parts = msg.split()
            data = get_query_month(parts[1] if len(parts) > 1 else None)
            if msg.startswith("查詢記帳"):
                push_result(_execute_query('query_expense', data, user_obj, setting, has_perm), 'query_expense')
            else:
                push_result(_execute_query('query_salary', data, user_obj, setting, has_perm), 'query_salary')
            return

        QUERY_SHORTCUTS = {
            '查詢預算':   'query_balance',
            '查詢生理期': 'query_period',
            '查詢倒數':   'query_countdown',
        }
        if msg in QUERY_SHORTCUTS:
            push_result(_execute_query(QUERY_SHORTCUTS[msg], {}, user_obj, setting, has_perm))
            return

        # ── 4. 快速記帳：記帳 <金額> <項目> [類別] ─────────────────
        import re as _re
        _time_re = _re.compile(r'^([01]?\d|2[0-3]):([0-5]\d)$')

        if msg.startswith('記帳 '):
            parts = msg.split()
            fmt   = '❌ 格式錯誤！\n正確格式：記帳 <金額> <項目> [類別]\n\n範例：\n記帳 85 午餐\n記帳 120 咖啡 飲食'
            if len(parts) >= 3:
                try:
                    amount   = float(parts[1])
                    name     = parts[2]
                    category = parts[3] if len(parts) >= 4 else '飲食'
                    if amount <= 0: raise ValueError
                    push_result(_execute_write('expense', {'amount': amount, 'name': name, 'category': category},
                                               user_obj, setting, has_perm), 'expense')
                except ValueError:
                    reply(fmt)
            else:
                reply(fmt)
            return

        # ── 5. 快速排班：排班 <開始> <結束> [日期] ─────────────────
        if msg.startswith('排班 '):
            def parse_time(s):
                s = s.strip().replace('.', ':')
                if len(s) == 4 and s.isdigit(): s = f'{s[:2]}:{s[2:]}'
                return s if _time_re.match(s) else None

            parts = msg.split()
            times, date_str = [], None
            for p in parts[1:]:
                if _re.match(r'^\d{4}-\d{2}-\d{2}$', p):
                    date_str = p
                else:
                    t = parse_time(p)
                    if t: times.append(t)

            if len(times) >= 2:
                data = {'start_time': times[0], 'end_time': times[1]}
                if date_str: data['date'] = date_str
                push_result(_execute_write('shift', data, user_obj, setting, has_perm), 'shift')
            else:
                reply('❌ 格式錯誤！\n正確格式：排班 <開始> <結束> [日期]\n\n範例：\n排班 14:00 21:00\n排班 1400 2100 2026-05-15')
            return

        # ── 6. 快速獎金：獎金 <金額> [備註] ────────────────────────
        if msg.startswith('獎金 '):
            parts = msg.split(maxsplit=2)
            try:
                amount = float(parts[1])
                if amount <= 0: raise ValueError
                note = parts[2] if len(parts) >= 3 else ''
                push_result(_execute_write('bonus', {'amount': amount, 'note': note},
                                           user_obj, setting, has_perm), 'shift')
            except (ValueError, IndexError):
                reply('❌ 格式錯誤！\n正確格式：獎金 <金額> [備註]\n\n範例：\n獎金 500\n獎金 1000 全勤獎金')
            return

        # ── 7. 快速生理期 ────────────────────────────────────────────
        if msg in ('生理期開始', '月經來了', '月經開始'):
            push_result(_execute_write('period', {'type': 'start'}, user_obj, setting, has_perm))
            return
        if msg in ('生理期結束', '月經結束'):
            push_result(_execute_write('period', {'type': 'end'}, user_obj, setting, has_perm))
            return

        # ── 8. 查詢 LINE ID ──────────────────────────────────────────
        if msg.strip() == "查詢":
            reply(f"您的 LINE User ID: {user_id}")
            return

        # ── 9. 其他訊息：顯示說明卡片 ───────────────────────────────
        from services.flex_message_service import FlexMessageService
        reply_flex("工具箱說明 — 左右滑動查看所有功能", FlexMessageService.build_help_carousel(),
                   qr=get_quick_replies())

    @handler.add(PostbackEvent)
    def handle_postback(event):
        user_id = event.source.user_id
        token   = getattr(event, 'reply_token', None)

        from urllib.parse import parse_qs
        qs     = parse_qs(event.postback.data)
        action = qs.get('action', [''])[0]

        if action == 'help':
            from services.flex_message_service import FlexMessageService
            LineService.push_flex(user_id, "工具箱說明 — 左右滑動查看所有功能",
                                  FlexMessageService.build_help_carousel(), reply_token=token)
        elif action == 'start_expense':
            LineService.push_message(user_id,
                "💰 快速記帳格式：\n記帳 <金額> <項目> [類別]\n\n範例：\n記帳 85 午餐\n記帳 120 咖啡 飲食",
                reply_token=token)
        elif action == 'start_shift':
            LineService.push_message(user_id,
                "🕒 快速排班格式：\n排班 <開始> <結束> [日期]\n\n範例：\n排班 14:00 21:00\n排班 1400 2100",
                reply_token=token)
