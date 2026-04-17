from flask import Blueprint, request, abort, current_app
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from services.line_service import LineService
from models import db, UserSettings
import os
from datetime import datetime

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
            # Find user with this valid binding code
            setting = UserSettings.query.filter_by(binding_code=msg).first()
            if setting:
                if setting.binding_expiry and setting.binding_expiry > datetime.now():
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

        # Find user if already bound
        setting = UserSettings.query.filter_by(line_user_id=user_id).first()

        # =============== SMART PARSERS =============== #
        
        # --- Common Date Parsing Magic ---
        def parse_date(d_str, default_dt):
            if not d_str: return default_dt
            formats = ["%H:%M", "%H%M", "%m/%d/%H:%M", "%m/%d %H:%M", "%Y/%m/%d/%H:%M", "%m/%d", "%Y/%m/%d"]
            for f in formats:
                try:
                    pd = datetime.strptime(d_str, f)
                    res = default_dt
                    if "%m" in f: res = res.replace(month=pd.month, day=pd.day)
                    if "%H" in f: res = res.replace(hour=pd.hour, minute=pd.minute, second=0)
                    if "%Y" in f: res = res.replace(year=pd.year)
                    if "%H" not in f and "%m" in f: res = res.replace(hour=12, minute=0, second=0)
                    return res
                except ValueError: pass
            return default_dt
        
        # 1. Expense: 記帳 [名稱] [類別：預設飲食] [金額] [預設時間(本年/本月/本日/現在時間)]
        if msg.startswith("記帳"):
            if not setting:
                LineService.push_message(user_id, "❌ 請先綁定帳號。")
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
            
            now_dt = datetime.now()
            final_time = parse_date(date_str, now_dt)
            now_str = final_time.strftime('%Y-%m-%d %H:%M:%S')
            
            from models import ExpenseRecord
            new_expense = ExpenseRecord(
                user_id=setting.user_id, timestamp=now_str, category=category, amount=amount, note=name
            )
            db.session.add(new_expense)
            db.session.commit()
            
            reply = f"✅ 新增支出\n📌 名稱：{name}\n💰 金額：${amount:g}\n🏷️ 類別：{category}\n⏰ 時間：{final_time.strftime('%m/%d %H:%M')}"
            LineService.push_message(user_id, reply)

        # 2. Bonus: 獎金 [金額] [時數(選填)] [備註(選填)]
        elif msg.startswith("獎金") or msg.startswith("薪水 獎金") or msg.startswith("薪資 獎金"):
            if not setting:
                LineService.push_message(user_id, "❌ 請先綁定帳號。")
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
            
            now_dt = datetime.now()
            final_time = parse_date(date_str, now_dt)
            now_date = final_time.strftime('%Y-%m-%d')
            
            from models import SalaryRecord
            new_salary = SalaryRecord(
                user_id=setting.user_id, date=now_date, type='bonus', amount=amount, hours=hours, note=note
            )
            db.session.add(new_salary)
            db.session.commit()
            
            reply = f"✅ 新增獎金\n💰 金額：${amount:,}\n⏱️ 時數：{hours:g} 小時\n📝 備註：{note if note else '無'}"
            LineService.push_message(user_id, reply)

        # 3. Shift: 排班 [開始時間(預設12:00)] [結束時間(預設18:00)] [自訂時薪(預設)] [備註]
        elif msg.startswith("排班") or msg.startswith("打工") or msg.startswith("薪水 排班"):
            if not setting:
                LineService.push_message(user_id, "❌ 請先綁定帳號。")
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
            from datetime import timedelta
            t1 = datetime.strptime(start_time, "%H:%M")
            t2 = datetime.strptime(end_time, "%H:%M")
            if t2 < t1: t2 += timedelta(days=1)
            hours = (t2 - t1).total_seconds() / 3600.0
            
            rate = custom_rate if custom_rate is not None else float(setting.hourly_rate or 196.0)
            
            now_dt = datetime.now()
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
            
            holiday_emoji = "🎆 " if (effective_rate == rate and amount == int(hours * rate * 2)) else ""
            reply = f"✅ 新增排班紀錄\n📅 日期：{final_time.strftime('%m/%d')}\n⏰ 時間：{start_time} ~ {end_time}\n⏱️ 時數：{hours:.1f} 小時\n💵 時薪：${rate:g}/hr\n{holiday_emoji}💰 金額：${amount:,}"
            if updated_note: reply += f"\n📝 備註：{updated_note}"
            LineService.push_message(user_id, reply)

        elif msg == "查詢":
             LineService.push_message(user_id, f"您的 LINE User ID: {user_id}")
             
        else:
            if setting:
                help_msg = "🤖 嗨！歡迎使用快速紀錄：\n\n📝 【記帳】\n指令：記帳 [類別] [金額] [項目名稱]\n範例：記帳 飲食 150 雞腿便當\n\n⏰ 【排班】\n指令：排班 [起] [迄] [時薪(選填)]\n範例：排班 0900 1800 200\n\n💰 【獎金】\n指令：獎金 [金額] [時數(選填)] [備註]\n範例：獎金 1500 4 三節獎金"
                LineService.push_message(user_id, help_msg)
            else:
                LineService.push_message(user_id, "🤖 我是工具箱小幫手。\n請先至系統網站設定頁面產生 6 位數驗證碼，綁定成功後就能用語音或文字快速記帳囉！")

# Hacky way to register handlers on import or first request?
# Better: In app factory, call a setup function.
