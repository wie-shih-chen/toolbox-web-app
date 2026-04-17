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
                # Check expiry
                if setting.binding_expiry and setting.binding_expiry > datetime.now():
                    setting.line_user_id = user_id
                    setting.binding_code = None # Clear code
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

        # Fast Expense Entry: "記帳 [類別] [金額] [備註可有可無]"
        if msg.startswith("記帳"):
            if not setting:
                LineService.push_message(user_id, "❌ 請先至系統網站設定頁面，產生並輸入 6 位數驗證碼進行綁定。")
                return
            
            from models import ExpenseRecord
            parts = [p for p in msg.split() if p.strip()]
            if len(parts) >= 3:
                try:
                    category = parts[1]
                    amount = float(parts[2])
                    note = " ".join(parts[3:]) if len(parts) > 3 else ""
                    
                    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    new_expense = ExpenseRecord(
                        user_id=setting.user_id,
                        timestamp=now_str,
                        category=category,
                        amount=amount,
                        note=note
                    )
                    db.session.add(new_expense)
                    db.session.commit()
                    
                    reply = f"✅ 記帳成功！\n\n📌 類別：{category}\n💰 金額：{amount:g}\n📝 備註：{note if note else '無'}\n📅 時間：{now_str.split()[0]}"
                    LineService.push_message(user_id, reply)
                except ValueError:
                    LineService.push_message(user_id, "❌ 金額格式錯誤，請輸入數字。\n範例：記帳 飲食 150 午餐")
            else:
                LineService.push_message(user_id, "❌ 格式錯誤。\n正確格式：記帳 [類別] [金額] [備註(可選)]\n範例：記帳 飲食 150 午餐")

        # Fast Salary Entry: "薪資 [類型] [金額] [備註可有可無]"
        elif msg.startswith("薪水") or msg.startswith("薪資"):
            if not setting:
                LineService.push_message(user_id, "❌ 請先至系統網站設定頁面，產生並輸入 6 位數驗證碼進行綁定。")
                return
            
            from models import SalaryRecord
            parts = [p for p in msg.split() if p.strip()]
            if len(parts) >= 3:
                try:
                    t_str = parts[1]
                    amount = int(float(parts[2])) 
                    note = " ".join(parts[3:]) if len(parts) > 3 else ""
                    
                    sType = 'bonus' if t_str != '打工' else 'shift'
                    
                    now_date = datetime.now().strftime('%Y-%m-%d')
                    new_salary = SalaryRecord(
                        user_id=setting.user_id,
                        date=now_date,
                        type=sType,
                        amount=amount,
                        note=note
                    )
                    db.session.add(new_salary)
                    db.session.commit()
                    
                    reply = f"✅ 薪資記錄成功！\n\n📌 類型：{t_str}\n💰 金額：{amount}\n📝 備註：{note if note else '無'}\n📅 日期：{now_date}"
                    LineService.push_message(user_id, reply)
                except ValueError:
                    LineService.push_message(user_id, "❌ 金額格式錯誤，請輸入數字。\n範例：薪資 獎金 1000 專案獎金")
            else:
                LineService.push_message(user_id, "❌ 格式錯誤。\n正確格式：薪資 [類型(打工/獎金)] [金額] [備註(可選)]\n範例：薪資 獎金 1000 專案獎金")

        elif msg == "查詢":
             LineService.push_message(user_id, f"您的 LINE User ID: {user_id}")
             
        else:
            if setting:
                help_msg = "🤖 嗨！告訴我支出或收入，我來幫你記下！\n\n📝 【快速記帳】\n輸入：記帳 [類別] [金額] [備註]\n範例：記帳 飲食 150 雞腿便當\n\n💰 【快速記薪】\n輸入：薪資 [類型] [金額] [備註]\n範例：薪資 獎金 1000 老闆發的"
                LineService.push_message(user_id, help_msg)
            else:
                LineService.push_message(user_id, "🤖 我是工具箱小幫手。\n請先至系統網站產生並輸入 6 位數驗證碼，綁定成功後就能用語音或文字快速記帳囉！")

# Hacky way to register handlers on import or first request?
# Better: In app factory, call a setup function.
