import os
import logging
from flask_apscheduler import APScheduler
from services.reminder_service import ReminderService
from services.calendar_notify_service import CalendarNotifyService
from services.countdown_notify_service import CountdownNotifyService
from services.period_notify_service import PeriodNotifyService
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime

logger = logging.getLogger(__name__)
scheduler = APScheduler()

def _send_company_notifications(app):
    """掃描所有公司的通知設定，依用戶總設定發送 LINE/Email 通知。"""
    from datetime import datetime
    import json
    try:
        with app.app_context():
            from models import db, Company, SalaryRecord, User
            from services.notification_service import NotificationTemplate

            now = datetime.now()
            today_day = now.day
            today_weekday = now.strftime('%A').lower()  # 'monday' .. 'sunday'
            current_time_str = now.strftime('%H:%M')

            companies = Company.query.filter_by(is_active=True).all()
            if not companies:
                return

            company_ids = [c.id for c in companies]
            # Fetch all users associated with these companies in one go to reduce queries
            users = {u.id: u for u in User.query.filter(User.id.in_(list(set(c.user_id for c in companies)))).all()}
            
            for company in companies:
                user = users.get(company.user_id)
                if not user or not user.settings:
                    continue

                try:
                    methods = json.loads(user.settings.notification_methods or '["email"]')
                except Exception:
                    methods = ['email']

                # ---- 發薪日通知 ----
                if (company.notify_payday_enabled and
                        today_day == company.notify_payday_day and
                        current_time_str == company.notify_payday_time):

                    # Calculate last month earnings
                    import calendar
                    last_month = now.month - 1 if now.month > 1 else 12
                    last_year = now.year if now.month > 1 else now.year - 1
                    last_day = calendar.monthrange(last_year, last_month)[1]
                    start = f"{last_year}-{last_month:02d}-01"
                    end = f"{last_year}-{last_month:02d}-{last_day:02d}"

                    records = SalaryRecord.query.filter(
                        SalaryRecord.user_id == user.id,
                        SalaryRecord.company_id == company.id,
                        SalaryRecord.date >= start,
                        SalaryRecord.date <= end
                    ).all()
                    total = sum(r.amount for r in records)
                    hours = sum(r.hours or 0 for r in records if r.type == 'shift')
                    msg = (f"📬 [{company.name}] 今天是發薪日！\n"
                           f"上月共排班 {hours:.1f} 小時\n"
                           f"預計收入 ${total:,}")

                    if 'line' in methods:
                        try:
                            from services.line_service import LineService
                            LineService.push_to_user(user.id, msg, module='salary')
                        except Exception as e:
                            logger.error(f"Company payday LINE error: {e}")
                    if 'email' in methods and user.email:
                        try:
                            from services.email_service import EmailService
                            EmailService.send_email(
                                to=user.email,
                                subject=f'[{company.name}] 發薪日提醒',
                                template='email/simple_notify.html',
                                username=user.username,
                                message=msg
                            )
                        except Exception as e:
                            logger.error(f"Company payday Email error: {e}")

                # ---- 每週摘要通知 ----
                if (company.notify_weekly_enabled and
                        today_weekday == company.notify_weekly_day and
                        current_time_str == company.notify_weekly_time):

                    # This week Monday to today
                    monday = now - __import__('datetime').timedelta(days=now.weekday())
                    start = monday.strftime('%Y-%m-%d')
                    end = now.strftime('%Y-%m-%d')
                    records = SalaryRecord.query.filter(
                        SalaryRecord.user_id == user.id,
                        SalaryRecord.company_id == company.id,
                        SalaryRecord.date >= start,
                        SalaryRecord.date <= end
                    ).all()
                    hours = sum(r.hours or 0 for r in records if r.type == 'shift')
                    total = sum(r.amount for r in records)
                    msg = (f"📊 [{company.name}] 本週工時摘要\n"
                           f"日期：{start} ~ {end}\n"
                           f"共排班 {hours:.1f} 小時，收入 ${total:,}")

                    if 'line' in methods:
                        try:
                            from services.line_service import LineService
                            LineService.push_to_user(user.id, msg, module='salary')
                        except Exception as e:
                            logger.error(f"Company weekly LINE error: {e}")
                    if 'email' in methods and user.email:
                        try:
                            from services.email_service import EmailService
                            EmailService.send_email(
                                to=user.email,
                                subject=f'[{company.name}] 每週工時摘要',
                                template='email/simple_notify.html',
                                username=user.username,
                                message=msg
                            )
                        except Exception as e:
                            logger.error(f"Company weekly Email error: {e}")
    except Exception as e:
        logger.error(f"Company notification error: {e}")

def _send_shift_reminders(app):
    """掃描所有公司的排班提醒規則，並發送通知。"""
    from datetime import datetime, timedelta
    import json
    try:
        with app.app_context():
            from models import db, Company, SalaryRecord, User, CompanyShiftReminder, ShiftReminderLog
            
            now = datetime.now()
            today_str = now.strftime('%Y-%m-%d')
            tomorrow_str = (now + timedelta(days=1)).strftime('%Y-%m-%d')
            
            # Fetch active reminders
            active_reminders = CompanyShiftReminder.query.filter_by(is_active=True).all()
            if not active_reminders:
                return
                
            # Batch fetch related companies and users
            company_ids = list(set(r.company_id for r in active_reminders))
            companies = {c.id: c for c in Company.query.filter(Company.id.in_(company_ids), Company.is_active == True).all()}
            user_ids = list(set(c.user_id for c in companies.values()))
            users = {u.id: u for u in User.query.filter(User.id.in_(user_ids)).all()}
            
            # Batch fetch shifts for today and tomorrow for all relevant companies
            all_shifts = SalaryRecord.query.filter(
                SalaryRecord.type == 'shift',
                SalaryRecord.company_id.in_(company_ids),
                SalaryRecord.date.in_([today_str, tomorrow_str])
            ).all()
            
            # Group shifts by company_id for quick lookup
            from collections import defaultdict
            shifts_by_company = defaultdict(list)
            for shift in all_shifts:
                shifts_by_company[shift.company_id].append(shift)

            for reminder in active_reminders:
                company = companies.get(reminder.company_id)
                if not company:
                    continue
                user = users.get(company.user_id)
                if not user or not user.settings:
                    continue
                    
                try:
                    methods = json.loads(user.settings.notification_methods or '["email"]')
                except Exception:
                    methods = ['email']
                    
                shifts = shifts_by_company.get(company.id, [])
                
                for shift in shifts:
                    if not shift.start_time:
                        continue
                    
                    try:
                        shift_start_dt = datetime.strptime(f"{shift.date} {shift.start_time}", "%Y-%m-%d %H:%M")
                    except ValueError:
                        continue
                        
                    # Calculate exactly when we should send the reminder
                    notify_dt = shift_start_dt + timedelta(minutes=reminder.offset_minutes)
                    
                    # If the notify time has passed and is within the last 15 minutes (to avoid sending very old ones if server was down)
                    if now >= notify_dt and now <= notify_dt + timedelta(minutes=15):
                        # Check if already sent
                        log_exists = ShiftReminderLog.query.filter_by(
                            shift_id=shift.id, 
                            reminder_id=reminder.id
                        ).first()
                        
                        if not log_exists:
                            # Send the reminder!
                            msg = reminder.message_template or "記得打卡！"
                            # Add dynamic variable replacements
                            msg = msg.replace("{time}", shift.start_time)
                            msg = msg.replace("{company}", company.name)
                            
                            final_msg = f"[{company.name} 排班提醒]\n{msg}"
                            
                            if 'line' in methods:
                                try:
                                    from services.line_service import LineService
                                    LineService.push_to_user(user.id, final_msg, module='salary')
                                except Exception as e:
                                    logger.error(f"Shift reminder LINE error: {e}")
                                    
                            if 'email' in methods and user.email:
                                try:
                                    from services.email_service import EmailService
                                    EmailService.send_email(
                                        to=user.email,
                                        subject=f'[{company.name}] 排班提醒',
                                        template='email/simple_notify.html',
                                        username=user.username,
                                        message=final_msg
                                    )
                                except Exception as e:
                                    logger.error(f"Shift reminder Email error: {e}")
                                    
                            # Save log
                            new_log = ShiftReminderLog(
                                shift_id=shift.id,
                                reminder_id=reminder.id,
                                sent_at=now
                            )
                            db.session.add(new_log)
            db.session.commit()
    except Exception as e:
        logger.error(f"Shift reminder task error: {e}")


class NotificationScheduler:
    @staticmethod
    def init_app(app):
        """Initialize APScheduler and register all notification tasks."""
        app.config['SCHEDULER_API_ENABLED'] = True
        scheduler.init_app(app)
        
        @scheduler.task('interval', id='check_reminders', seconds=60)
        def check_reminders_task():
            # Wrap in app context inside the task
            with app.app_context():
                ReminderService.check_and_send_reminders(app)
        
        @scheduler.task('interval', id='calendar_notify', seconds=60)
        def calendar_notify_task():
            """Every minute: check if any user's notify_time matches now → send calendar reminders."""
            CalendarNotifyService.check_and_send(app)

        @scheduler.task('cron', id='countdown_notify', hour=9, minute=0)
        def countdown_notify_task():
            """Every day at 09:00 TW time, send countdown/anniversary milestone reminders."""
            CountdownNotifyService.check_and_send(app)

        @scheduler.task('interval', id='period_notify', seconds=60)
        def period_notify_task():
            """Every minute: check if any user's period notice matches now."""
            PeriodNotifyService.check_and_send(app)

        @scheduler.task('interval', id='company_notify', seconds=60)
        def company_notify_task():
            """Every minute: check company payday / weekly summary notifications, and shift reminders."""
            _send_company_notifications(app)
            _send_shift_reminders(app)

        if not os.environ.get('SKIP_SCHEDULER'):
            def recurring_finance_job():
                with app.app_context():
                    try:
                        from services.recurring_finance_service import RecurringFinanceService
                        print(f"[{datetime.now()}] [Scheduler] Running recurring finance check...")
                        RecurringFinanceService.check_and_create(app)
                    except Exception as e:
                        print(f"[{datetime.now()}] [Scheduler] Error in recurring finance task: {e}")

            scheduler.add_job(
                func=recurring_finance_job,
                trigger=CronTrigger(hour=8, minute=0),
                id='recurring_finance_job',
                name='Recurring Finance Job',
                replace_existing=True
            )
            
            scheduler.add_job(
                func=recurring_finance_job,
                trigger='date',
                run_date=datetime.now(),
                id='recurring_finance_job_startup',
                name='Recurring Finance Job Startup'
            )

            try:
                import fcntl
                # Use a file lock to ensure only one worker starts the scheduler
                lock_file_path = os.path.join(os.environ.get('TMPDIR', '/tmp'), 'apscheduler.lock')
                scheduler_lock_file = open(lock_file_path, 'w')
                try:
                    # LOCK_NB means non-blocking; raises BlockingIOError if already locked
                    fcntl.lockf(scheduler_lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    scheduler.start()
                    logger.info("NotificationScheduler started successfully.")
                    print("Scheduler started successfully.")
                    # Keep scheduler_lock_file open for the lifetime of this process
                    app.scheduler_lock_file = scheduler_lock_file
                except BlockingIOError:
                    logger.info("Scheduler already running in another worker.")
                    print("Scheduler already running in another worker.")
            except Exception as e:
                logger.error(f"Failed to start NotificationScheduler: {e}")
                print(f"Failed to start Scheduler: {e}")
                print("Reminders will not be sent automatically.")
        else:
            logger.info("NotificationScheduler start skipped (SKIP_SCHEDULER set).")
            print("Scheduler start skipped (SKIP_SCHEDULER set).")
