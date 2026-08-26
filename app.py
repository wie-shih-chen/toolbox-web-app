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

@login_manager.request_loader
def load_user_from_request(request):
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header.replace('Bearer ', '', 1)
        import jwt
        from config import Config
        try:
            payload = jwt.decode(token, Config.SECRET_KEY, algorithms=['HS256'])
            user_id = payload.get('user_id')
            if user_id:
                return User.query.get(int(user_id))
        except:
            return None
    return None

@app.context_processor
def inject_globals():
    import json
    def parse_dock_order(user):
        default = ["main.index", "salary.index", "ntut.calendar", "expense.today"]
        if user and user.is_authenticated and user.settings and user.settings.dock_order:
            try:
                return json.loads(user.settings.dock_order)
            except:
                return default
        return default
    return dict(parse_dock_order=parse_dock_order)

# Register Blueprints
with app.app_context():
    db.create_all() # Create tables if they don't exist (checkfirst is default in SQLAlchemy 2.x)

    from routes.main_routes import main_bp
    from routes.salary_routes import salary_bp
    from routes.download_routes import download_bp
    from routes.ntut_routes import ntut_bp
    from routes.expense_routes import expense_bp
    from routes.auth import auth_bp
    from routes.shop import shop_bp
    from routes.admin import admin_bp
    from routes.finance_routes import finance_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(salary_bp, url_prefix='/salary')
    app.register_blueprint(download_bp, url_prefix='/download')
    app.register_blueprint(ntut_bp)
    app.register_blueprint(expense_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(shop_bp, url_prefix='/shop')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(finance_bp, url_prefix='/finance')
    
    from services.line_service import LineService
    from routes.line_routes import line_bp, register_line_handlers
    
    # Initialize LINE Service
    LineService.init_app(app)
    register_line_handlers(LineService.get_handler())
    
    app.register_blueprint(line_bp, url_prefix='/line')
    
    from routes.reminder_routes import reminder_bp
    app.register_blueprint(reminder_bp, url_prefix='/reminders')

    from routes.period_routes import period_bp
    app.register_blueprint(period_bp)

    from routes.countdown_routes import countdown_bp
    app.register_blueprint(countdown_bp)

    from routes.vocab_routes import vocab_bp
    app.register_blueprint(vocab_bp, url_prefix='/vocab')

    from routes.custom_vocab_routes import custom_vocab_bp
    app.register_blueprint(custom_vocab_bp, url_prefix='/vocab')

    from routes.group_routes import group_bp
    app.register_blueprint(group_bp, url_prefix='/group')



    # Initialize Scheduler
    try:
        from services.notification_scheduler import NotificationScheduler
        NotificationScheduler.init_app(app)
    except ImportError as e:
        print(f"Scheduler could not start: {e}")
        print("Reminders will not be sent automatically.")
    except Exception as e:
        print(f"Scheduler error: {e}")


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5001)
