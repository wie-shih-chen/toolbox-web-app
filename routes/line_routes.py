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

        # 1. Fast Expense Entry: "記帳 [類別] [金額] [備註可有可無]"
        if msg.startswith("記帳"):
            if not setting:
                LineService.push_message(user_id, "❌ 請先至系統網站設定頁面，產生並輸入 6 位數驗證碼進行綁定。")
                return
            
            parts = [p for p in msg.split() if p.strip()]
            if len(parts) < 3:
                LineService.push_message(user_id, "❌ 缺少必填資料！\n格式：記帳 [類別] [金額] [備註(選填)]\n範例：記帳 飲食 150 午餐")
                return
                
            from models import ExpenseRecord
            category = parts[1]
            try:
                amount = float(parts[2])
                if amount <= 0: raise ValueError
            except:
                LineService.push_message(user_id, "❌ 金額格式不正確，請輸入大於 0 的數字。\n範例：記帳 飲食 150")
                return
                
            note = " ".join(parts[3:]) if len(parts) > 3 else ""
            now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            new_expense = ExpenseRecord(
                user_id=setting.user_id, timestamp=now_str, category=category, amount=amount, note=note
            )
            db.session.add(new_expense)
            db.session.commit()
            
            reply = f"✅ 記帳成功\n📌 類別：{category}\n💰 金額：${amount:g}\n📝 備註：{note if note else '無'}"
            LineService.push_message(user_id, reply)

        # 2. Fast Bonus Entry: "獎金 [金額] [備註可有可無]"
        elif msg.startswith("獎金") or msg.startswith("薪水 獎金") or msg.startswith("薪資 獎金"):
            if not setting:
                LineService.push_message(user_id, "❌ 請先綁定帳號。")
                return
                
            parts = [p for p in msg.split() if p.strip()]
            # If msg starts with "薪水 獎金", skip first two, else skip first
            val_idx = 2 if "薪" in parts[0] else 1
            
            if len(parts) <= val_idx:
                LineService.push_message(user_id, "❌ 缺少必填資料！\n格式：獎金 [金額] [備註(選填)]\n範例：獎金 1500 三節獎金")
                return
                
            try:
                amount = int(float(parts[val_idx]))
                if amount <= 0: raise ValueError
            except:
                LineService.push_message(user_id, "❌ 金額格式不正確，請輸入大於 0 的整數。")
                return
                
            note = " ".join(parts[val_idx+1:]) if len(parts) > val_idx+1 else ""
            now_date = datetime.now().strftime('%Y-%m-%d')
            
            from models import SalaryRecord
            new_salary = SalaryRecord(
                user_id=setting.user_id, date=now_date, type='bonus', amount=amount, note=note
            )
            db.session.add(new_salary)
            db.session.commit()
            
            reply = f"✅ 獎金入帳\n💰 金額：${amount:,}\n📝 備註：{note if note else '無'}"
            LineService.push_message(user_id, reply)

        # 3. Fast Shift Entry: "排班 [開始時間] [結束時間] [備註可有可無]"
        elif msg.startswith("排班") or msg.startswith("打工") or msg.startswith("薪水 排班"):
            if not setting:
                LineService.push_message(user_id, "❌ 請先綁定帳號。")
                return
                
            parts = [p for p in msg.split() if p.strip()]
            idx_start = 2 if "薪" in parts[0] else 1
            
            if len(parts) < idx_start + 2:
                LineService.push_message(user_id, "❌ 缺少起訖時間！\n格式：排班 [開始時間] [結束時間] [備註(選填)]\n範例：排班 09:00 18:00")
                return
                
            start_str = parts[idx_start].replace(".", ":")
            end_str = parts[idx_start+1].replace(".", ":")
            
            # Format validation
            import re
            time_pattern = re.compile(r"^([01]?[0-9]|2[0-3]):?([0-5][0-9])$")
            m_start = time_pattern.match(start_str)
            m_end = time_pattern.match(end_str)
            
            if not (m_start and m_end):
                LineService.push_message(user_id, "❌ 時間格式錯誤！\n請使用 HH:MM，例如 09:00 或直接輸入 0900")
                return
                
            def fmt(m): return f"{int(m.group(1)):02d}:{m.group(2)}"
            start_time = fmt(m_start)
            end_time = fmt(m_end)
            
            # Compute hours
            from datetime import timedelta
            t1 = datetime.strptime(start_time, "%H:%M")
            t2 = datetime.strptime(end_time, "%H:%M")
            if t2 < t1: t2 += timedelta(days=1)
            hours = (t2 - t1).total_seconds() / 3600.0
            
            rate = float(setting.hourly_rate or 183.0)
            note = " ".join(parts[idx_start+2:]) if len(parts) > idx_start+2 else ""
            now_date = datetime.now().strftime('%Y-%m-%d')
            
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
            
            is_holiday = effective_rate == rate and amount == int(hours * rate * 2) # simplified check
            holiday_emoji = "🎆 " if is_holiday else ""
            reply = f"✅ 排班記錄成功！\n\n⏰ 時間：{start_time} ~ {end_time}\n⏱️ 時數：{hours:.1f} 小時\n{holiday_emoji}💰 金額：${amount:,}\n📝 備註：{note if note else '無'}"
            LineService.push_message(user_id, reply)

        elif msg == "查詢":
             LineService.push_message(user_id, f"您的 LINE User ID: {user_id}")
             
        else:
            if setting:
                help_msg = "🤖 嗨！歡迎使用快速紀錄：\n\n📝 【記帳】\n指令：記帳 [類別] [金額] [備註]\n範例：記帳 飲食 150 晚餐\n\n⏰ 【排班】\n指令：排班 [起] [迄] [備註]\n範例：排班 0900 1800 (自動算薪水)\n\n💰 【獎金】\n指令：獎金 [金額] [備註]\n範例：獎金 1500 三節獎金"
                LineService.push_message(user_id, help_msg)
            else:
                LineService.push_message(user_id, "🤖 我是工具箱小幫手。\n請先至系統網站設定頁面產生 6 位數驗證碼，綁定成功後就能用語音或文字快速記帳囉！")

# Hacky way to register handlers on import or first request?
# Better: In app factory, call a setup function.
