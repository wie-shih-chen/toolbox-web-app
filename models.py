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
    
    # Relationships
    salary_records = db.relationship('SalaryRecord', backref='user', lazy=True)
    expense_records = db.relationship('ExpenseRecord', backref='user', lazy=True)
    settings = db.relationship('UserSettings', backref='user', uselist=False, lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

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
