from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True) # Making nullable first for migration
    password_hash = db.Column(db.String(120), nullable=False)
    
    # Avatar
    avatar_type = db.Column(db.String(20), default='preset') # 'preset' or 'upload'
    avatar_val = db.Column(db.String(255), default='default') # preset name or file path
    
    # Relationships
    salary_records = db.relationship('SalaryRecord', backref='user', lazy=True)
    expense_records = db.relationship('ExpenseRecord', backref='user', lazy=True)
    settings = db.relationship('UserSettings', backref='user', uselist=False, lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_reset_token(self, expires_sec=1800):
        from flask import current_app
        from itsdangerous import URLSafeTimedSerializer as Serializer
        s = Serializer(current_app.config['SECRET_KEY'])
        return s.dumps({'user_id': self.id}, salt='password-reset-salt')

    @staticmethod
    def verify_reset_token(token, expires_sec=1800):
        from flask import current_app
        from itsdangerous import URLSafeTimedSerializer as Serializer
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            user_id = s.loads(token, salt='password-reset-salt', max_age=expires_sec)['user_id']
        except:
            return None
        return User.query.get(user_id)

class SalaryRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.String(10), nullable=False) # YYYY-MM-DD
    type = db.Column(db.String(20), nullable=False) # 'shift' or 'bonus'
    
    # Shift details
    start_time = db.Column(db.String(5)) # HH:MM
    end_time = db.Column(db.String(5))   # HH:MM
    hours = db.Column(db.Float, default=0.0)
    rate = db.Column(db.Float, default=0.0)
    
    # Common details
    amount = db.Column(db.Integer, default=0)
    note = db.Column(db.String(200))

class ExpenseRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.String(20), nullable=False) # YYYY-MM-DD HH:MM:SS
    category = db.Column(db.String(50))
    note = db.Column(db.String(200))
    amount = db.Column(db.Float, default=0.0)

class UserSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Salary settings
    hourly_rate = db.Column(db.Float, default=183.0)
    
    # Expense settings
    monthly_budget = db.Column(db.Float, default=10000.0)
    
    # New Fields
    editable_month_range = db.Column(db.Integer, default=1) # 0=Current, 1=Prev, -1=Unlimited
    
    # Salary
    default_start_time = db.Column(db.String(5), default='09:00')
    default_end_time = db.Column(db.String(5), default='18:00')
    target_income = db.Column(db.Integer, default=0)
    
    # Expense
    budget_alert_threshold = db.Column(db.Integer, default=80)
    
    # Advanced Expense Features
    billing_cycle_start_day = db.Column(db.Integer, default=10)
    custom_categories = db.Column(db.Text, default='[]')      # JSON list of category objects
    recurring_expenses = db.Column(db.Text, default='[]')     # JSON list of recurring expense objects
    quick_shortcuts = db.Column(db.Text, default='[]')        # JSON list of shortcut strings
    
    # LINE Bot Integration
    line_user_id = db.Column(db.String(255), nullable=True)   # The user's unique LINE User ID
    binding_code = db.Column(db.String(6), nullable=True)     # 6-digit random code
    binding_expiry = db.Column(db.DateTime, nullable=True)    # Code expiration time
    notification_methods = db.Column(db.Text, default='["email"]') # JSON list: ["email", "line"]
    monthly_report_day = db.Column(db.Integer, default=5) # 1-28

class ReportLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    period_start = db.Column(db.String(10), nullable=False) # YYYY-MM-DD
    period_end = db.Column(db.String(10), nullable=False)   # YYYY-MM-DD
    report_type = db.Column(db.String(20), nullable=False)  # 'salary' or 'expense'

    sent_at = db.Column(db.String(20), nullable=False)      # Timestamp

class Reminder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    
    # Frequency: 'once', 'daily', 'weekly', 'monthly'
    frequency = db.Column(db.String(20), default='once')
    
    # Time settings
    remind_time = db.Column(db.String(5), nullable=False) # HH:MM
    remind_date = db.Column(db.String(10), nullable=True) # YYYY-MM-DD (for 'once')
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    last_sent_at = db.Column(db.DateTime, nullable=True)
    
    # Notification Method JSON list: ["line", "email"]
    notify_method = db.Column(db.Text, default='["line"]') 
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

