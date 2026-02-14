import os
from dotenv import load_dotenv

# Load environment variables from .env file before importing config
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))

from flask import Flask, render_template
from config import Config
from models import db, User, ReportLog
from flask_login import LoginManager
from extensions import mail

app = Flask(__name__)
app.config.from_object(Config)

# Initialize Extensions
db.init_app(app)
mail.init_app(app)
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Register Blueprints
with app.app_context():
    db.create_all() # Create tables if they don't exist

    from routes.main_routes import main_bp
    from routes.salary_routes import salary_bp
    from routes.download_routes import download_bp
    from routes.ntut_routes import ntut_bp
    from routes.expense_routes import expense_bp
    from routes.auth import auth_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(salary_bp, url_prefix='/salary')
    app.register_blueprint(download_bp, url_prefix='/download')
    app.register_blueprint(ntut_bp)
    app.register_blueprint(expense_bp)
    app.register_blueprint(auth_bp)
    
    from services.line_service import LineService
    from routes.line_routes import line_bp, register_line_handlers
    
    # Initialize LINE Service
    LineService.init_app(app)
    register_line_handlers(LineService.get_handler())
    
    app.register_blueprint(line_bp, url_prefix='/line')
    
    from routes.reminder_routes import reminder_bp
    app.register_blueprint(reminder_bp, url_prefix='/reminders')

    # Initialize Scheduler
    try:
        from flask_apscheduler import APScheduler
        from services.reminder_service import ReminderService
        
        scheduler = APScheduler()
        app.config['SCHEDULER_API_ENABLED'] = True
        scheduler.init_app(app)
        
        @scheduler.task('interval', id='check_reminders', seconds=60)
        def check_reminders_task():
            # Wrap in app context inside the task
            with app.app_context():
                ReminderService.check_and_send_reminders(app)
            
        scheduler.start()
        print("Scheduler started successfully.")
    except ImportError as e:
        print(f"Scheduler could not start: {e}")
        print("Reminders will not be sent automatically.")
    except Exception as e:
        print(f"Scheduler error: {e}")


if __name__ == '__main__':
    app.run(debug=True, port=5001)
