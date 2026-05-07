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
        
        # Check if message is a 6-digit number (Binding Code)
        if msg.isdigit() and len(msg) == 6:
            setting = UserSettings.query.filter_by(binding_code=msg).first()
            if setting:
                if setting.binding_expiry and setting.binding_expiry > datetime.utcnow():
                    # Check if this LINE ID already has a binding
                    existing = LineBinding.query.filter_by(line_user_id=user_id).first()
                    if existing:
                        LineService.push_message(user_id, "⚠️ 此 LINE 帳號已綁定過其他帳號，請先解除舊的綁定。")
                        return
                    # Create new LineBinding with full permissions
                    existing_count = LineBinding.query.filter_by(user_id=setting.user_id).count()
                    auto_nickname = f'使用者 {existing_count + 1}'
                    new_binding = LineBinding(
                        user_id=setting.user_id,
                        line_user_id=user_id,
                        nickname=auto_nickname,
                        permissions=json.dumps(["expense", "salary", "period"])
                    )
                    db.session.add(new_binding)
                    # Also keep backward-compat field updated
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

        # Find binding record for this LINE user
        binding = LineBinding.query.filter_by(line_user_id=user_id).first()
        # Fallback: support old-style single binding via UserSettings.line_user_id
        if not binding:
            old_setting = UserSettings.query.filter_by(line_user_id=user_id).first()
            if old_setting:
                # Auto-migrate on-the-fly
                binding = LineBinding(
                    user_id=old_setting.user_id,
                    line_user_id=user_id,
                    nickname='本人',
                    permissions=json.dumps(["expense", "salary", "period"])
                )
                db.session.add(binding)
                db.session.commit()

        setting = UserSettings.query.filter_by(user_id=binding.user_id).first() if binding else None

        def has_perm(perm):
            """Check if this LINE binding has the given permission."""
            if not binding: return False
            try:
                perms = json.loads(binding.permissions or '[]')
            except Exception:
                perms = []
            return perm in perms

        # =============== SMART PARSERS =============== #
        
        # --- Common Date Parsing Helper ---
        def parse_date(d_str, default_dt):
            """Parse a flexible date/time string, always anchored to default_dt's year."""
            if not d_str:
                return default_dt
            current_year = default_dt.year
            # Inject year into month/day-only strings so strptime doesn't pick ambiguous year
            enriched = d_str
            import re as _re
            if _re.match(r'^\d{1,2}/\d{1,2}$', d_str):
                enriched = f"{current_year}/{d_str}"
            formats = [
                ("%Y/%m/%d/%H:%M", True, True, True),
                ("%Y/%m/%d", True, True, False),
                ("%m/%d/%H:%M", False, True, True),
                ("%H:%M", False, False, True),
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
            """Helper to get start_date and end_date for a given month string (e.g. '4月', '11').
               Defaults to current month if None or invalid."""
            now = datetime.utcnow() + timedelta(hours=8)
            year = now.year
            month = now.month
            
            if month_str:
                import re
                match = re.search(r'(\d+)', month_str)
                if match:
                    parsed_month = int(match.group(1))
                    if 1 <= parsed_month <= 12:
                        month = parsed_month
                        # If user queries a future month (e.g. querying December in Jan), it's probably last year.
                        if month > now.month:
                            year -= 1
            
            import calendar
            last_day = calendar.monthrange(year, month)[1]
            start_date = f"{year}-{month:02d}-01"
            end_date = f"{year}-{month:02d}-{last_day}"
            return start_date, end_date

        if msg.startswith("查詢記帳"):
            if not binding:
                LineService.push_message(user_id, "❌ 請先綁定帳號。")
                return
            if not has_perm("expense"):
                LineService.push_message(user_id, "⛔ 此帳號無記帳權限，請聯絡帳號擁有者開啟。")
                return
                
            parts = msg.split()
            month_str = parts[1] if len(parts) > 1 else None
            start_date, end_date = get_query_month_range(month_str)
            
            user_obj = User.query.get(binding.user_id)
            from services.expense_service import ExpenseService
            expense_svc = ExpenseService()
            summary = expense_svc.get_summary(start_date, end_date, user=user_obj)
            
            total = summary.get('total_amount', 0)
            records = summary.get('records', [])
            
            # Categories stat
            from collections import defaultdict
            category_stats = defaultdict(lambda: {'count': 0, 'amount': 0, 'emoji': '📦'})
            for r in records:
                cat_full = r.get('category', '其他')
                c_parts = cat_full.split(' ')
                emoji = c_parts[0] if len(c_parts) > 1 else '📦'
                cat_name = c_parts[1] if len(c_parts) > 1 else cat_full
                category_stats[cat_name]['count'] += 1
                category_stats[cat_name]['amount'] += int(r['amount'])
                category_stats[cat_name]['emoji'] = emoji
            
            from services.flex_message_service import FlexMessageService
            flex = FlexMessageService.build_expense_summary(
                username=user_obj.username, start_date=start_date, end_date=end_date,
                total=total, category_stats=category_stats, records=records
            )
            LineService.push_flex(user_id, f"{start_date[5:7]}月份記帳總覽", flex)
            return

        elif msg.startswith("查詢薪水") or msg.startswith("查詢薪資"):
            if not binding:
                LineService.push_message(user_id, "❌ 請先綁定帳號。")
                return
            if not has_perm("salary"):
                LineService.push_message(user_id, "⛔ 此帳號無薪資管理權限，請聯絡帳號擁有者開啟。")
                return
                
            parts = msg.split()
            month_str = parts[1] if len(parts) > 1 else None
            start_date, end_date = get_query_month_range(month_str)
            
            user_obj = User.query.get(binding.user_id)
            from services.salary_service import SalaryService
            salary_svc = SalaryService()
            summary = salary_svc.get_history_summary(start_date, end_date, user=user_obj)
            
            total_amt = summary.get('total_amount', 0)
            total_hrs = summary.get('total_hours', 0)
            records = summary.get('records', [])
            
            # Type stats
            from collections import defaultdict
            type_stats = defaultdict(lambda: {'count': 0, 'amount': 0, 'hours': 0})
            for r in records:
                rtype = "排班" if r['type'] == 'shift' else "獎金"
                if r['type'] != 'shift' and r['type'] != 'bonus': rtype = r['type']
                type_stats[rtype]['count'] += 1
                type_stats[rtype]['amount'] += r.get('amount', 0)
                if r['type'] == 'shift':
                    type_stats[rtype]['hours'] += r.get('hours', 0)
                    
            from services.flex_message_service import FlexMessageService
            flex = FlexMessageService.build_salary_summary(
                username=user_obj.username, start_date=start_date, end_date=end_date,
                total_amt=total_amt, total_hrs=total_hrs, type_stats=type_stats, records=records
            )
            LineService.push_flex(user_id, f"{start_date[5:7]}月份薪資總覽", flex)
            return

        # 1. Expense: 記帳 [名稱] [類別：預設飲食] [金額] [預設時間(本年/本月/本日/現在時間)]
        if msg.startswith("記帳"):
            if not binding:
                LineService.push_message(user_id, "❌ 請先綁定帳號。")
                return
            if not has_perm("expense"):
                LineService.push_message(user_id, "⛔ 此帳號無記帳權限，請聯絡帳號擁有者開啟。")
                return
                
            if msg.strip() == "記帳":
                help_msg = (
                    "✏️ 準備記帳了嗎？請直接輸入您花費的項目與金額：\n\n"
                    "👉 例如：記帳 午餐 150\n"
                    "👉 例如：記帳 咖啡 飲食 65\n\n"
                    "💡 或者點選單右下角「開啟網站」，在網頁版上記帳更直覺喔！"
                )
                LineService.push_message(user_id, help_msg)
                return
            
            parts = [p for p in msg.split() if p.strip()][1:]
            amount = None
            date_str = None
            text_parts = []
            
            for p in parts:
                if amount is None:
                    try:
                        val = float(p)
                        if val > 0:
                            amount = val
                            continue
                    except ValueError: pass
                # Check for date formats (like 4/18 or 18:00 or 0900)
                if date_str is None and ('/' in p or ':' in p or '.' in p or (len(p)==4 and p.isdigit())):
                    date_str = p.replace('.', ':')
                    continue
                text_parts.append(p)
                
            if amount is None:
                LineService.push_message(user_id, "❌ 找不到金額！\n最少填寫：記帳 [名稱/備註] [金額]\n💡例如：記帳 午餐 150")
                return
                
            name = text_parts[0] if len(text_parts) > 0 else "隨手記"
            category = text_parts[1] if len(text_parts) > 1 else "飲食"
            if len(text_parts) > 2:
                name = " ".join(text_parts) # combine everything else as name/note if it's super long
                category = "飲食"
            
            now_dt = datetime.utcnow() + timedelta(hours=8)
            final_time = parse_date(date_str, now_dt)
            now_str = final_time.strftime('%Y-%m-%d %H:%M:%S')
            
            from models import ExpenseRecord
            new_expense = ExpenseRecord(
                user_id=setting.user_id, timestamp=now_str, category=category, amount=amount, note=name
            )
            db.session.add(new_expense)
            db.session.commit()
            
            from services.flex_message_service import FlexMessageService
            flex = FlexMessageService.build_expense_confirm(name=name, amount=amount, category=category, timestamp=now_str)
            LineService.push_flex(user_id, f"支出記錄成功：{name} ${amount:g}", flex)

        # 2. Bonus: 獎金 [金額] [時數(選填)] [備註(選填)]
        elif msg.startswith("獎金") or msg.startswith("薪水 獎金") or msg.startswith("薪資 獎金"):
            if not binding:
                LineService.push_message(user_id, "❌ 請先綁定帳號。")
                return
            if not has_perm("salary"):
                LineService.push_message(user_id, "⛔ 此帳號無薪資管理權限，請聯絡帳號擁有者開啟。")
                return
                
            parts = [p for p in msg.split() if p.strip()][1:]
            if parts and "薪" in parts[0]: parts = parts[1:] # strip 薪水
            
            amounts = []
            text_parts = []
            date_str = None
            
            for p in parts:
                if date_str is None and '/' in p:
                    date_str = p
                    continue
                try:
                    val = float(p)
                    amounts.append(val)
                except ValueError:
                    text_parts.append(p)
            
            if not amounts or amounts[0] <= 0:
                LineService.push_message(user_id, "❌ 找不到金額！\n最少填寫：獎金 [金額]\n💡例如：獎金 1500 三節")
                return
                
            amount = int(amounts[0])
            hours = amounts[1] if len(amounts) > 1 else 0.0
            note = " ".join(text_parts)
            
            now_dt = datetime.utcnow() + timedelta(hours=8)
            final_time = parse_date(date_str, now_dt)
            now_date = final_time.strftime('%Y-%m-%d')
            
            from models import SalaryRecord
            new_salary = SalaryRecord(
                user_id=setting.user_id, date=now_date, type='bonus', amount=amount, hours=hours, note=note
            )
            db.session.add(new_salary)
            db.session.commit()
            
            from services.flex_message_service import FlexMessageService
            flex = FlexMessageService.build_salary_confirm(record_type='bonus', date=now_date, amount=amount, hours=hours, note=note)
            LineService.push_flex(user_id, f"獎金記錄成功：${amount:,}", flex)

        # 3. Shift: 排班 [開始時間(預設12:00)] [結束時間(預設18:00)] [自訂時薪(預設)] [備註]
        elif msg.startswith("排班") or msg.startswith("打工") or msg.startswith("薪水 排班"):
            if not binding:
                LineService.push_message(user_id, "❌ 請先綁定帳號。")
                return
            if not has_perm("salary"):
                LineService.push_message(user_id, "⛔ 此帳號無薪資管理權限，請聯絡帳號擁有者開啟。")
                return
                
            parts = [p for p in msg.split() if p.strip()][1:]
            if parts and "薪" in parts[0]: parts = parts[1:]
            
            times = []
            amounts = []
            text_parts = []
            date_str = None
            
            for p in parts:
                if date_str is None and '/' in p:
                    date_str = p
                    continue
                # heuristic for time: contains colon/dot or is 4 plain digits
                if ':' in p or '.' in p or (len(p)==4 and p.isdigit()):
                    times.append(p)
                else:
                    try:
                        val = float(p)
                        amounts.append(val)
                    except ValueError:
                        text_parts.append(p)
            
            start_str = times[0] if len(times) > 0 else "12:00"
            end_str = times[1] if len(times) > 1 else "18:00"
            custom_rate = amounts[0] if len(amounts) > 0 else None
            note = " ".join(text_parts)
            
            # Format validation func
            def fmt(t_str):
                import re
                if len(t_str) == 4 and t_str.isdigit():
                    t_str = f"{t_str[:2]}:{t_str[2:]}"
                t_str = t_str.replace('.', ':')
                if not re.match(r"^([01]?[0-9]|2[0-3]):([0-5][0-9])$", t_str): return None
                return t_str
            
            start_time = fmt(start_str)
            end_time = fmt(end_str)
            
            if not (start_time and end_time):
                LineService.push_message(user_id, "❌ 時間格式錯誤！請使用 18:00 或 1800。")
                return
            
            # Compute hours
            t1 = datetime.strptime(start_time, "%H:%M")
            t2 = datetime.strptime(end_time, "%H:%M")
            if t2 < t1: t2 += timedelta(days=1)
            hours = (t2 - t1).total_seconds() / 3600.0
            
            rate = custom_rate if custom_rate is not None else float(setting.hourly_rate or 196.0)
            
            now_dt = datetime.utcnow() + timedelta(hours=8)
            final_time = parse_date(date_str, now_dt)
            now_date = final_time.strftime('%Y-%m-%d')
            
            from services.salary_service import _apply_holiday_pay
            effective_rate, amount, updated_note = _apply_holiday_pay(now_date, rate, hours, note)
            
            from models import SalaryRecord
            new_salary = SalaryRecord(
                user_id=setting.user_id, date=now_date, type='shift',
                start_time=start_time, end_time=end_time, hours=hours,
                rate=effective_rate, amount=amount, note=updated_note
            )
            db.session.add(new_salary)
            db.session.commit()
            
            from services.flex_message_service import FlexMessageService
            flex = FlexMessageService.build_salary_confirm(
                record_type='shift', date=now_date, amount=amount, hours=hours,
                start_time=start_time, end_time=end_time, note=updated_note
            )
            LineService.push_flex(user_id, f"排班記錄成功：{now_date} {start_time}~{end_time}", flex)

        # 4. Period: 月經 [起] [迄] [備註]  OR  月經 結束 [結束日期]
        elif msg.startswith("月經") or msg.startswith("生理期") or msg.startswith("mc") or msg.startswith("MC"):
            if not binding:
                LineService.push_message(user_id, "❌ 請先綁定帳號。")
                return
            if not has_perm("period"):
                LineService.push_message(user_id, "⛔ 此帳號無生理期記錄權限，請聯絡帳號擁有者開啟。")
                return

            original_msg = msg
            if msg.lower().startswith("mc"): original_msg = original_msg[2:]
            else: original_msg = original_msg[2:] # 月經 or 生理期(3 but we just split so doesn't matter)
            # Actually just split msg
            parts = [p for p in msg.split() if p.strip()][1:]
            
            dates = []
            text_parts = []
            for p in parts:
                if '/' in p:
                    dates.append(p)
                else:
                    text_parts.append(p)
            
            note = " ".join(text_parts).strip()
            now_dt = datetime.utcnow() + timedelta(hours=8)
            
            from services.period_service import PeriodService
            period_svc = PeriodService(setting.user_id)
            history = period_svc.get_history()
            latest = history[0] if history else None
            
            if "結束" in note:
                if not latest or latest['end_date']:
                    LineService.push_message(user_id, "❌ 目前沒有進行中的生理期可以結束喔！")
                    return
                end_str = dates[0] if len(dates) > 0 else None
                end_dt = parse_date(end_str, now_dt)
                end_date_fmt = end_dt.strftime('%Y-%m-%d')
                
                period_svc.update_record(latest['id'], start_date=latest['start_date'], end_date=end_date_fmt, note=latest['note'])
                LineService.push_message(user_id, f"🩸 結束生理期紀錄\n📅 開始：{latest['start_date'][5:].replace('-', '/')}\n📅 結束：{end_dt.strftime('%m/%d')}")
                return
            
            # Start a new period
            start_str = dates[0] if len(dates) > 0 else None
            end_str = dates[1] if len(dates) > 1 else None
            
            start_dt = parse_date(start_str, now_dt)
            start_date_fmt = start_dt.strftime('%Y-%m-%d')
            
            end_date_fmt = None
            if end_str:
                end_dt = parse_date(end_str, now_dt)
                end_date_fmt = end_dt.strftime('%Y-%m-%d')
            
            result = period_svc.add_record(start_date=start_date_fmt, end_date=end_date_fmt, note=note if note else None)
            
            if not result.get("success"):
                LineService.push_message(user_id, f"❌ {result.get('error', '新增失敗')}")
                return
            
            reply = f"🩸 新增生理期紀錄\n📅 開始：{start_dt.strftime('%m/%d')}"
            if end_date_fmt: reply += f"\n📅 結束：{end_dt.strftime('%m/%d')}"
            if note: reply += f"\n📝 備註：{note}"
            LineService.push_message(user_id, reply)

        elif msg == "查詢":
             LineService.push_message(user_id, f"您的 LINE User ID: {user_id}")
             
        else:
            if setting:
                # Try Gemini NLP parsing first if API key is set
                gemini_key = current_app.config.get('GEMINI_API_KEY')
                if gemini_key and len(msg) < 200:
                    try:
                        from google import genai
                        client = genai.Client(api_key=gemini_key)
                        
                        now_dt = datetime.utcnow() + timedelta(hours=8)
                        now_str = now_dt.strftime('%Y-%m-%d %H:%M')
                        weekday_map = {1: '一', 2: '二', 3: '三', 4: '四', 5: '五', 6: '六', 7: '日'}
                        weekday = weekday_map[now_dt.isoweekday()]

                        prompt = f"""你是一個智慧記帳與生活管家。現在時間是 {now_str} (星期{weekday})。
使用者輸入：「{msg}」

請分析使用者的語意，並「只」回傳以下其中一種 JSON 格式（不要有 ```json 標籤）：

【情況 1：記帳支出】(花錢)
{{"action": "expense", "date": "YYYY-MM-DD", "name": "項目名稱", "amount": 數字, "category": "飲食/交通/娛樂/居住/其他"}}

【情況 2：排班打工】(上班)
{{"action": "shift", "date": "YYYY-MM-DD", "start_time": "HH:MM", "end_time": "HH:MM", "note": "備註"}}

【情況 3：薪資獎金】(拿到錢)
{{"action": "bonus", "date": "YYYY-MM-DD", "amount": 數字, "note": "備註"}}

【情況 4：生理期】(月經來或結束)
{{"action": "period", "type": "start" 或 "end", "date": "YYYY-MM-DD", "note": "備註"}}

【情況 5：無法辨識】
{{"action": "unknown"}}

請特別注意：如果使用者提到「昨天」、「上週五」、「前天」等時間詞，請利用上方提供的「現在時間」精準推算正確的 YYYY-MM-DD。若無提到時間，預設為今天的日期。
"""
                        response = client.models.generate_content(
                            model='gemini-2.5-flash',
                            contents=prompt
                        )
                        res_text = response.text.strip()
                        if res_text.startswith("```json"):
                            res_text = res_text[7:]
                        if res_text.endswith("```"):
                            res_text = res_text[:-3]
                            
                        import json
                        ai_data = json.loads(res_text.strip())
                        action = ai_data.get("action", "unknown")
                        
                        if action == "expense":
                            if not has_perm("expense"):
                                LineService.push_message(user_id, "⛔ 此帳號無記帳權限，無法新增。")
                                return
                                
                            name = ai_data.get("name", "隨手記")
                            amount = ai_data.get("amount", 0)
                            category = ai_data.get("category", "其他")
                            date_str = ai_data.get("date", now_dt.strftime('%Y-%m-%d'))
                            record_time = f"{date_str} {now_dt.strftime('%H:%M:%S')}"
                            
                            from models import ExpenseRecord
                            new_expense = ExpenseRecord(
                                user_id=setting.user_id, timestamp=record_time, category=category, amount=amount, note=name
                            )
                            db.session.add(new_expense)
                            db.session.commit()
                            
                            from services.flex_message_service import FlexMessageService
                            flex = FlexMessageService.build_expense_confirm(name=name, amount=amount, category=category, timestamp=record_time, ai=True)
                            LineService.push_flex(user_id, f"AI 自動記帳：{name} ${amount:g}", flex)
                            return
                            
                        elif action == "shift":
                            if not has_perm("salary"):
                                LineService.push_message(user_id, "⛔ 此帳號無薪資管理權限，無法新增。")
                                return
                            date_str = ai_data.get("date", now_dt.strftime('%Y-%m-%d'))
                            start_time = ai_data.get("start_time", "12:00")
                            end_time = ai_data.get("end_time", "18:00")
                            note = ai_data.get("note", "")
                            
                            t1 = datetime.strptime(start_time, "%H:%M")
                            t2 = datetime.strptime(end_time, "%H:%M")
                            if t2 < t1: t2 += timedelta(days=1)
                            hours = (t2 - t1).total_seconds() / 3600.0
                            
                            rate = float(setting.hourly_rate or 196.0)
                            amount = hours * rate
                            
                            from models import SalaryRecord
                            new_salary = SalaryRecord(
                                user_id=setting.user_id, date=date_str, type='shift', amount=amount, hours=hours, note=note, start_time=start_time, end_time=end_time, rate=rate
                            )
                            db.session.add(new_salary)
                            db.session.commit()
                            from services.flex_message_service import FlexMessageService
                            flex = FlexMessageService.build_salary_confirm(
                                record_type='shift', date=date_str, amount=amount, hours=hours,
                                start_time=start_time, end_time=end_time, note=note, ai=True
                            )
                            LineService.push_flex(user_id, f"AI 自動排班：{date_str} {start_time}~{end_time}", flex)
                            return
                            
                        elif action == "bonus":
                            if not has_perm("salary"):
                                LineService.push_message(user_id, "⛔ 此帳號無薪資管理權限，無法新增。")
                                return
                            date_str = ai_data.get("date", now_dt.strftime('%Y-%m-%d'))
                            amount = ai_data.get("amount", 0)
                            note = ai_data.get("note", "")
                            
                            from models import SalaryRecord
                            new_salary = SalaryRecord(
                                user_id=setting.user_id, date=date_str, type='bonus', amount=amount, hours=0, note=note
                            )
                            db.session.add(new_salary)
                            db.session.commit()
                            from services.flex_message_service import FlexMessageService
                            flex = FlexMessageService.build_salary_confirm(record_type='bonus', date=date_str, amount=amount, note=note, ai=True)
                            LineService.push_flex(user_id, f"AI 自動獎金：${amount:,}", flex)
                            return
                            
                        elif action == "period":
                            if not has_perm("period"):
                                LineService.push_message(user_id, "⛔ 此帳號無月經紀錄權限，無法新增。")
                                return
                                
                            ptype = ai_data.get("type", "start")
                            date_str = ai_data.get("date", now_dt.strftime('%Y-%m-%d'))
                            note = ai_data.get("note", "")
                            
                            from services.period_service import PeriodService
                            period_svc = PeriodService(setting.user_id)
                            
                            if ptype == "end":
                                history = period_svc.get_history()
                                latest = history[0] if history else None
                                if not latest or latest['end_date']:
                                    LineService.push_message(user_id, "❌ 目前沒有進行中的生理期可以結束喔！")
                                    return
                                period_svc.update_record(latest['id'], start_date=latest['start_date'], end_date=date_str, note=latest['note'])
                                LineService.push_message(user_id, f"✨ 生理期結束 (AI)\n📅 結束日期：{date_str}")
                            else:
                                result = period_svc.add_record(start_date=date_str, end_date=None, note=note)
                                if not result.get("success"):
                                    LineService.push_message(user_id, f"❌ {result.get('error')}")
                                    return
                                reply = f"✨ 新增生理期 (AI)\n📅 開始日期：{date_str}"
                                if note: reply += f"\n📝 備註：{note}"
                                LineService.push_message(user_id, reply)
                            return
                    except Exception as e:
                        current_app.logger.error(f"Gemini AI Error: {str(e)}")
                        # Fallback to help message if AI fails

                help_msg = (
                    "🤖 嗨！我聽不太懂，但你可以用以下格式快速帶入資料：\n\n"
                    "📝 【記帳】 記帳 [名稱] [類別(預設飲食)] [金額] [日期時間(可省)]\n"
                    "👉 範例：記帳 午餐 150 4/18\n\n"
                    "⏰ 【排班】 排班 [起] [迄] [時薪(可省)] [日期(可省)] [備註]\n"
                    "👉 範例：排班 4/18 1200 1800\n\n"
                    "💰 【獎金】 獎金 [金額] [日期(可省)] [時數(可省)] [備註]\n"
                    "👉 範例：獎金 1500 4/18 三節發放\n\n"
                    "🩸 【月經】 月經 [開始(可省)] [結束(可省)] [備註]\n"
                    "👉 範例1：月經\n"
                    "👉 範例2：月經 4/18 4/22\n"
                    "👉 範例3：月經 結束\n\n"
                    "💡 小提示：順序可以隨便打，只要有數字和日期（如 4/18），我就會聰明地幫你歸位喔！\n\n"
                    "🔍 【查詢】 查詢記帳 [月份(可省)] 或 查詢薪水 [月份(可省)]\n"
                    "👉 範例1：查詢記帳\n"
                    "👉 範例2：查詢薪水 4月"
                )
                LineService.push_message(user_id, help_msg)
            else:
                LineService.push_message(user_id, "🤖 我是工具箱小幫手。\n請先至系統網站設定頁面產生 6 位數驗證碼，綁定成功後就能用語音或文字快速記帳囉！")

# Hacky way to register handlers on import or first request?
# Better: In app factory, call a setup function.
