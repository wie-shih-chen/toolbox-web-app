from flask import Blueprint, current_app, request, jsonify
from datetime import datetime
import os
import logging

from services.reminder_service import ReminderService
from services.calendar_notify_service import CalendarNotifyService
from services.countdown_notify_service import CountdownNotifyService
from services.period_notify_service import PeriodNotifyService
from services.notification_scheduler import _send_company_notifications, _send_shift_reminders
from services.recurring_finance_service import RecurringFinanceService

cron_bp = Blueprint('cron_bp', __name__)
logger = logging.getLogger(__name__)

# 全域變數，紀錄每天只執行一次的任務是否已經執行過
_daily_tasks_executed_today = False
_last_execution_date = None

@cron_bp.route('/cron/trigger', methods=['GET', 'POST'])
def trigger_all_tasks():
    """
    Cloud Scheduler 每分鐘會呼叫這個端點一次。
    為了安全起見，我們檢查 request 裡的 cron_secret。
    """
    secret = request.args.get('secret') or request.headers.get('X-Cron-Secret')
    if secret != os.environ.get('CRON_SECRET'):
        return jsonify({'error': 'Unauthorized'}), 401

    app = current_app._get_current_object()
    now = datetime.now()
    results = []

    # ==========================================
    # 1. 每分鐘都要檢查的任務
    # ==========================================
    try:
        ReminderService.check_and_send_reminders(app)
        results.append("Reminders checked")
    except Exception as e:
        logger.error(f"Reminder error: {e}")

    try:
        CalendarNotifyService.check_and_send(app)
        results.append("Calendar checked")
    except Exception as e:
        logger.error(f"Calendar error: {e}")

    try:
        PeriodNotifyService.check_and_send(app)
        results.append("Period checked")
    except Exception as e:
        logger.error(f"Period error: {e}")

    try:
        _send_company_notifications(app)
        _send_shift_reminders(app)
        results.append("Company/Shift checked")
    except Exception as e:
        logger.error(f"Company/Shift error: {e}")

    # ==========================================
    # 2. 每天只執行一次的任務 (例如早上 8 點與 9 點的任務)
    # 這裡為求簡化，我們把它合併在早上 8 點後統一觸發，或者獨立檢查時間
    # ==========================================
    global _daily_tasks_executed_today, _last_execution_date
    current_date = now.date()

    if _last_execution_date != current_date:
        _daily_tasks_executed_today = False
        _last_execution_date = current_date

    # 如果現在時間大於早上 8 點，且今天還沒執行過
    if now.hour >= 8 and not _daily_tasks_executed_today:
        try:
            RecurringFinanceService.check_and_create(app)
            results.append("Recurring finance created")
            
            CountdownNotifyService.check_and_send(app)
            results.append("Countdown notified")
            
            _daily_tasks_executed_today = True
        except Exception as e:
            logger.error(f"Daily tasks error: {e}")

    return jsonify({
        'status': 'success',
        'time': str(now),
        'tasks_run': results
    }), 200
