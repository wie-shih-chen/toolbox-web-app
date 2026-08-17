import os
import logging
from flask_apscheduler import APScheduler
from services.reminder_service import ReminderService
from services.calendar_notify_service import CalendarNotifyService
from services.countdown_notify_service import CountdownNotifyService
from services.period_notify_service import PeriodNotifyService

logger = logging.getLogger(__name__)
scheduler = APScheduler()

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

        @scheduler.task('interval', id='countdown_notify', seconds=60)
        def countdown_notify_task():
            """Every minute: at 09:00 TW time, send countdown/anniversary milestone reminders."""
            CountdownNotifyService.check_and_send(app)

        @scheduler.task('interval', id='period_notify', seconds=60)
        def period_notify_task():
            """Every minute: check if any user's period notice matches now."""
            PeriodNotifyService.check_and_send(app)
            
        if not os.environ.get('SKIP_SCHEDULER'):
            try:
                scheduler.start()
                logger.info("NotificationScheduler started successfully.")
                print("Scheduler started successfully.")
            except Exception as e:
                logger.error(f"Scheduler could not start: {e}")
                print(f"Scheduler could not start: {e}")
                print("Reminders will not be sent automatically.")
        else:
            logger.info("NotificationScheduler start skipped (SKIP_SCHEDULER set).")
            print("Scheduler start skipped (SKIP_SCHEDULER set).")
