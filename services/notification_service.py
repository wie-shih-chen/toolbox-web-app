from flask import current_app
from extensions import mail
from flask_mail import Message
import json
import logging

logger = logging.getLogger(__name__)

class NotificationTemplate:
    """
    統一管理所有推播通知的文字內容，方便一次性檢修與修改。
    """
    
    # --- 1. 行事曆 (Calendar) ---
    @staticmethod
    def get_calendar_msg(event_title, cal_name):
        return f"📅 行事曆提醒：明天 {event_title}\n（日曆：{cal_name}）"
        
    @staticmethod
    def get_calendar_subject(event_title):
        return f"📅 行事曆提醒：明天 {event_title}"

    # --- 2. 倒數日 (Countdown) ---
    @staticmethod
    def get_countdown_msg(title, milestone_label):
        return f"💕 「{title}」提醒：明天是 {milestone_label}"
        
    @staticmethod
    def get_countdown_subject(msg_text):
        return f"💕 倒數日提醒：{msg_text[:50]}"

    # --- 3. 日常提醒 (Reminder) ---
    @staticmethod
    def get_reminder_msg(title, description, remind_time):
        return f"🔔 [提醒] {title}\n\n{description or ''}\n\n時間: {remind_time}"
        
    @staticmethod
    def get_reminder_subject(title):
        return f"🔔 提醒: {title}"

    # --- 4. 生理期 (Period) ---
    @staticmethod
    def get_period_msg(days_before, date_str):
        return f"🩸 生理期提醒：預計在 {days_before} 天後 ({date_str}) 開始，請預作準備！"
        
    @staticmethod
    def get_period_subject():
        return "🩸 生理期提醒"

    # --- 5. 排卵期 (Ovulation) ---
    @staticmethod
    def get_ovulation_msg(days_before, date_str):
        return f"🌸 排卵期提醒：預計在 {days_before} 天後 ({date_str}) 到來，這段期間受孕機率較高哦！"
        
    @staticmethod
    def get_ovulation_subject():
        return "🌸 排卵期提醒"

    # --- 6. 薪資 (Salary) ---
    @staticmethod
    def get_salary_export_msg(username, records, total_amount, type_stats, start_date=None, end_date=None):
        if start_date and end_date:
            msg = (
                f"📊 [薪資匯出] {username}\n"
                f"期間: {start_date} ~ {end_date}\n"
                f"總金額: ${total_amount:,}\n"
                f"總筆數: {len(records)} 筆\n"
                f"------------------\n"
            )
        else:
            from datetime import datetime
            msg = (
                f"📊 [薪資匯出通知] {username}\n"
                f"總筆數: {len(records)}\n"
                f"總金額: ${total_amount:,}\n"
                f"匯出時間: {datetime.now().strftime('%Y/%m/%d %H:%M')}\n"
                f"------------------\n"
            )
            
        msg += "【項目統計】\n"
        for rtype, stats in type_stats.items():
            line_stat = f"💰 {rtype}: ${stats['amount']:,} ({stats['count']}筆"
            if stats['hours'] > 0:
                line_stat += f", 共{stats['hours']}h"
            line_stat += ")\n"
            msg += line_stat
            
        msg += "------------------\n【明細紀錄】\n"
        detail_lines = []
        for r in records:
            rtype = "排班" if r['type'] == 'shift' else "獎金"
            if r['type'] not in ['shift', 'bonus']:
                rtype = r['type']
            line = f"{r['date'][5:]} {rtype} ${r['amount']}"
            if r['type'] == 'shift':
                line += f" ({r['hours']}h)"
            detail_lines.append(line)
        msg += "\n".join(detail_lines)
        return msg

    @staticmethod
    def get_salary_report_msg(start_date, end_date, total_salary, records):
        msg = (
            f"💰 [薪資報表] {start_date} ~ {end_date}\n"
            f"總金額: ${total_salary:,}\n"
            f"筆數: {len(records)} 筆\n"
            f"------------------\n"
        )
        detail_lines = []
        for r in records:
            rtype = "排班" if r['type'] == 'shift' else "獎金"
            if r['type'] not in ['shift', 'bonus']:
                rtype = r['type']
            line = f"{r['date'][5:]} {rtype} ${r['amount']}"
            if r['type'] == 'shift':
                line += f" ({r['hours']}h)"
            detail_lines.append(line)
        msg += "\n".join(detail_lines)
        return msg

    # --- 7. 記帳 (Expense) ---
    @staticmethod
    def get_expense_export_msg(start_date, end_date, total_expense, records, category_stats):
        msg = f"📊 【記帳報表】 {start_date} ~ {end_date}\n"
        msg += f"💰 總支出: ${int(total_expense):,}\n"
        msg += f"📝 總筆數: {len(records)} 筆\n"
        msg += "🔍 類別統計:\n"
        
        # Format category stats
        for cat, stats in sorted(category_stats.items(), key=lambda x: x[1]['amount'], reverse=True):
            amount = stats['amount']
            if amount > 0:
                pct = (amount / total_expense) * 100 if total_expense > 0 else 0
                emoji = stats.get('emoji', '📦')
                msg += f"  {emoji} {cat}: ${int(amount):,} ({pct:.1f}%)\n"
                
        msg += "------------------\n"
        msg += "【明細紀錄】\n"
        
        detail_lines = []
        current_week = None
        
        def get_week_range(date_str):
            from datetime import datetime, timedelta
            dt = datetime.strptime(date_str[:10], '%Y-%m-%d')
            start = dt - timedelta(days=dt.weekday())
            end = start + timedelta(days=6)
            return start.strftime('%m/%d'), end.strftime('%m/%d')
            
        for r in records:
            cat = r.get('category', '其他')
            note = str(r.get('note', '')).strip()
            if not note or note.lower() == 'none':
                note = '(無備註)'
            
            w_start, w_end = get_week_range(r['timestamp'])
            week_str = f"{w_start} ~ {w_end}"
            if week_str != current_week:
                detail_lines.append(f"════ [ {week_str} ] ════")
                current_week = week_str
                
            time_str = r['timestamp'][5:16].replace('-', '/')
            amt_str = f"${int(r['amount']):,}"
            detail_lines.append(f"{time_str} {cat} [{amt_str}] {note}")
            
        msg += "\n".join(detail_lines)
        return msg

    @staticmethod
    def get_expense_report_msg(start_date, end_date, total_amount, records):
        msg = (
            f"💸 [記帳報表] {start_date} ~ {end_date}\n"
            f"總支出: ${total_amount:,}\n"
            f"------------------\n"
        )
        detail_lines = []
        for r in records:
            cat = r.get('category', '其他').split(' ')[0]
            detail_lines.append(f"{r['timestamp'][5:16]} {cat} ${int(r['amount'])}")
        msg += "\n".join(detail_lines)
        return msg

    # --- 8. 自動固定收支 (Recurring) ---
    @staticmethod
    def get_recurring_expense_msg(name, amount, category):
        return f"🤖 [系統自動扣款] 已為您新增一筆固定支出：\n名稱：{name}\n類別：{category}\n金額：${amount:,}"
        
    @staticmethod
    def get_recurring_expense_subject(name):
        return f"🤖 固定支出自動扣款：{name}"

class NotificationService:
    @staticmethod
    def send_notification(user, subject, message_text, notify_methods=None, module=None):
        """
        Sends a notification to the user via their preferred methods.
        If notify_methods is None, checks user.settings.notification_methods or defaults to ['email'].
        Returns True if at least one method succeeded.
        """
        if notify_methods is None:
            if hasattr(user, 'settings') and user.settings and hasattr(user.settings, 'notification_methods') and user.settings.notification_methods:
                try:
                    notify_methods = json.loads(user.settings.notification_methods)
                except:
                    notify_methods = ['email']
            else:
                notify_methods = ['email']
                
        if not notify_methods:
            return False
            
        success = False
        prefix = f"[{module or 'System'}] "
        
        # 1. LINE Notify
        if 'line' in notify_methods:
            try:
                from services.line_service import LineService
                if LineService.push_to_user(user.id, message_text, module=module):
                    print(f"{prefix}LINE sent to user {user.id}")
                    success = True
            except Exception as e:
                print(f"{prefix}LINE send failed for user {user.id}: {e}")

        # 2. Email Notify
        if 'email' in notify_methods and user.email:
            try:
                sender = current_app.config.get('MAIL_USERNAME')
                msg = Message(
                    subject=subject,
                    recipients=[user.email],
                    body=message_text,
                    sender=sender
                )
                mail.send(msg)
                print(f"{prefix}Email sent to {user.email}")
                success = True
            except Exception as e:
                print(f"{prefix}Email send failed for user {user.id}: {e}")
                
        return success
