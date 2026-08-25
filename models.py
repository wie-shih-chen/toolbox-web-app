from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True) # Making nullable first for migration
    password_hash = db.Column(db.String(120), nullable=False)
    
    # Avatar
    avatar_type = db.Column(db.String(20), default='preset') # 'preset' or 'upload'
    avatar_val = db.Column(db.String(255), default='default') # preset name or file path
    
    # Roles and Permissions
    role = db.Column(db.String(10), default='member')  # 'admin' | 'member'
    can_mark_paid = db.Column(db.Boolean, default=False)
    
    
    # Relationships
    salary_records = db.relationship('SalaryRecord', backref='user', lazy=True)
    expense_records = db.relationship('ExpenseRecord', backref='user', lazy=True)
    period_records = db.relationship('PeriodRecord', backref='user', lazy=True)
    settings = db.relationship('UserSettings', backref='user', uselist=False, lazy='joined')
    reminders = db.relationship('Reminder', backref='user', lazy=True)
    line_bindings = db.relationship('LineBinding', backref='user', lazy=True)
    orders = db.relationship('Order', backref='user', lazy=True)
    cart = db.relationship('CartItem', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == 'admin'

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

class Company(db.Model):
    """Per-user company profile for multi-company salary tracking."""
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name        = db.Column(db.String(100), nullable=False)
    color       = db.Column(db.String(10), default='#6366f1')   # hex color for badge
    hourly_rate = db.Column(db.Float, default=183.0)
    # Per-company notification settings
    notify_payday_enabled = db.Column(db.Boolean, default=False)
    notify_payday_day     = db.Column(db.Integer, default=10)    # day of month
    notify_payday_time    = db.Column(db.String(5), default='09:00')
    notify_weekly_enabled = db.Column(db.Boolean, default=False)
    notify_weekly_day     = db.Column(db.String(10), default='sunday')
    notify_weekly_time    = db.Column(db.String(5), default='20:00')
    break_rules = db.Column(db.Text, default='[]') # JSON list of rules e.g. [{"threshold": 4.0, "deduct": 0.5}]
    is_active   = db.Column(db.Boolean, default=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    salary_records = db.relationship('SalaryRecord', backref='company', lazy=True)

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
    
    # Company association (nullable for backward compatibility)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=True)

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

class CompanyShiftReminder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    offset_minutes = db.Column(db.Integer, default=0) # Negative = before start, 0 = at start, Positive = after start
    message_template = db.Column(db.String(200), default="記得打卡！")
    is_active = db.Column(db.Boolean, default=True)

class ShiftReminderLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    shift_id = db.Column(db.Integer, db.ForeignKey('salary_record.id'), nullable=False)
    reminder_id = db.Column(db.Integer, db.ForeignKey('company_shift_reminder.id'), nullable=False)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)

class UserSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Salary settings
    hourly_rate = db.Column(db.Float, default=183.0)
    
    # Expense settings
    monthly_budget = db.Column(db.Float, default=10000.0)
    
    # Finance settings (理財總覽)
    initial_assets = db.Column(db.Float, default=0.0)
    target_savings_rate = db.Column(db.Float, default=20.0)
    finance_cycle_type = db.Column(db.String(20), default='month') # 'month' 或 'billing'
    fixed_extra_income = db.Column(db.Float, default=0.0)
    enable_monthly_savings = db.Column(db.Boolean, default=False)
    monthly_savings_amount = db.Column(db.Integer, default=0)
    asset_tracking_start_date = db.Column(db.String(10), nullable=True) # YYYY-MM-DD
    
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
    
    # Layout Preferences
    dashboard_order = db.Column(db.Text, default='[]')
    dock_order = db.Column(db.Text, default='["main.index", "salary.index", "ntut.calendar", "expense.today"]')

    # Calendar notification settings
    calendar_notify_enabled = db.Column(db.Boolean, default=True)
    calendar_notify_time = db.Column(db.String(5), default='20:00')  # HH:MM

    # Built-in calendar display settings
    builtin_salary_name  = db.Column(db.String(50), default='🏷 班表')
    builtin_salary_color = db.Column(db.String(10), default='#6366f1')
    builtin_period_name  = db.Column(db.String(50), default='🩸 週期追蹤')
    builtin_period_color = db.Column(db.String(10), default='#ff4d4f')

    # Menstrual Cycle settings
    avg_period_cycle = db.Column(db.Integer, default=28)
    avg_period_duration = db.Column(db.Integer, default=5)
    period_notify_enabled = db.Column(db.Boolean, default=True)
    period_notify_time = db.Column(db.String(5), default='08:00')   # HH:MM
    period_notify_days_before = db.Column(db.Integer, default=3)
    period_notify_period = db.Column(db.Boolean, default=True)      # 🩸 月經前通知
    period_notify_ovulation = db.Column(db.Boolean, default=False)  # 🥚 排卵期前通知
    
    # Menstrual Environment Factors (0.0 to 1.0)
    stress_level = db.Column(db.Float, default=0.0)
    sleep_quality = db.Column(db.Float, default=0.5)
    anxiety_multiplier = db.Column(db.Float, default=0.0)

    # Vocab Settings
    vocab_daily_goal = db.Column(db.Integer, default=20)

class PeriodRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    start_date = db.Column(db.String(10), nullable=False) # YYYY-MM-DD
    end_date = db.Column(db.String(10), nullable=True)    # YYYY-MM-DD
    cycle_length = db.Column(db.Integer, nullable=True)   # Length since previous period
    note = db.Column(db.String(255), nullable=True)
    exclude_from_avg = db.Column(db.Boolean, default=False) # Skip this cycle in calculations
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

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
    
    # Custom Weekdays (for 'weekly' frequency)
    # JSON list of integers: 0=Mon, 1=Tue, ..., 6=Sun
    # Example: "[0, 2, 4]" for Mon, Wed, Fri
    weekdays = db.Column(db.String(50), nullable=True)

    # Status
    is_active = db.Column(db.Boolean, default=True)
    last_sent_at = db.Column(db.DateTime, nullable=True)
    
    # Notification Method JSON list: ["line", "email"]
    notify_method = db.Column(db.Text, default='["line"]') 
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class UserCalendar(db.Model):
    """Stores user-added ICS calendar sources (URL or uploaded file)."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    source_type = db.Column(db.String(10), nullable=False)  # 'url' or 'file'
    source = db.Column(db.String(500), nullable=False)       # URL or absolute file path
    color = db.Column(db.String(10), default='#4285F4')
    notify_enabled = db.Column(db.Boolean, default=True)    # Per-calendar mute toggle
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class CalendarNotificationLog(db.Model):
    """Tracks sent calendar event notifications to prevent duplicates."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    cal_id = db.Column(db.Integer, nullable=False)
    # Unique key: "{cal_id}:{start_date}:{title[:100]}" to identify the event
    event_key = db.Column(db.String(350), nullable=False)
    # The date this notification was sent (= day before event)
    sent_date = db.Column(db.String(10), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class PeriodNotificationLog(db.Model):
    """Tracks sent period notifications to prevent duplicates for the same predicted cycle."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    # The predicted start date this notification is for
    predicted_start_date = db.Column(db.String(10), nullable=False)
    # The date this notification was sent
    sent_date = db.Column(db.String(10), nullable=False)
    # The type of notification sent ('period' or 'ovulation')
    notify_type = db.Column(db.String(20), default='period')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Countdown(db.Model):
    """Countdown and Anniversary events."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    target_date = db.Column(db.String(10), nullable=False)  # YYYY-MM-DD
    is_anniversary = db.Column(db.Boolean, default=False)
    icon = db.Column(db.String(10), default='📅')
    image_path = db.Column(db.String(255), nullable=True) # For custom uploaded photos
    pinned = db.Column(db.Boolean, default=False)
    notify_enabled = db.Column(db.Boolean, default=True) # Notification toggle
    repeat_annually = db.Column(db.Boolean, default=False)  # For fixed annual holidays
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class CountdownSubEvent(db.Model):
    """Custom milestones/events attached to a parent Countdown/Anniversary."""
    id = db.Column(db.Integer, primary_key=True)
    countdown_id = db.Column(db.Integer, db.ForeignKey('countdown.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    target_date = db.Column(db.String(10), nullable=False)  # YYYY-MM-DD
    icon = db.Column(db.String(10), default='📅')
    repeat_annually = db.Column(db.Boolean, default=False)  # If True, repeat on same month/day every year
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class LineBinding(db.Model):
    """A LINE account bound to a web account, with per-binding permission control."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    line_user_id = db.Column(db.String(255), unique=True, nullable=False)
    nickname = db.Column(db.String(50), default='未命名')
    # JSON list of allowed actions: "expense", "salary", "period"
    permissions = db.Column(db.Text, default='["expense","salary","period"]')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class LineConversationSession(db.Model):
    """
    儲存每位 LINE 用戶的多輪對話狀態。
    - state: IDLE（空閒）or COLLECTING（AI 正在收集資料中）
    - intent: 本輪對話的意圖（expense / shift / bonus / period）
    - collected_data: JSON，已收集到的欄位值
    - pending_fields: JSON list，尚待追問的必填欄位
    - updated_at: 自動更新，超過 30 分鐘視為過期並重置
    """
    __tablename__ = 'line_conversation_sessions'
    id = db.Column(db.Integer, primary_key=True)
    line_user_id = db.Column(db.String(255), unique=True, nullable=False, index=True)
    state = db.Column(db.String(20), default='IDLE')           # IDLE / COLLECTING
    intent = db.Column(db.String(50), nullable=True)            # expense / shift / bonus / period
    collected_data = db.Column(db.Text, default='{}')           # JSON: 已收集欄位
    pending_fields = db.Column(db.Text, default='[]')           # JSON list: 待追問欄位
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SSOUsedToken(db.Model):
    """
    記錄已使用的 SSO JWT jti（JWT ID），防止重放攻擊。
    jti 是 UUID4，每個 token 只能使用一次。
    自動清理超過 30 分鐘的記錄（在 sso-token 端點觸發清理）。
    """
    __tablename__ = 'sso_used_tokens'
    jti      = db.Column(db.String(36), primary_key=True)   # UUID4
    used_at  = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


# ========================================================
# Shopping Models
# ========================================================

class Product(db.Model):
    __tablename__ = 'products'
    id          = db.Column(db.Integer, primary_key=True)
    code        = db.Column(db.String(50), unique=True, nullable=True)   # 草稿時可為 null
    name        = db.Column(db.String(100), nullable=True)
    price       = db.Column(db.Float, nullable=True)
    sizes_json  = db.Column(db.Text, default='[]')    # JSON list e.g. ["S","M","L"]
    colors      = db.Column(db.String(200), nullable=True)
    description = db.Column(db.Text, nullable=True)
    status      = db.Column(db.String(10), default='draft')  # 'draft' | 'published'
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    images      = db.relationship('ProductImage', backref='product',
                                  lazy=True, order_by='ProductImage.order_index',
                                  cascade='all, delete-orphan')
    cart_items  = db.relationship('CartItem', backref='product', lazy=True)
    order_items = db.relationship('OrderItem', backref='product', lazy=True)

    @property
    def sizes(self):
        try:
            return json.loads(self.sizes_json or '[]')
        except Exception:
            return []

    @sizes.setter
    def sizes(self, val):
        self.sizes_json = json.dumps(val, ensure_ascii=False)

    @property
    def primary_image(self):
        for img in self.images:
            if img.is_primary:
                return img
        return self.images[0] if self.images else None

    @property
    def is_published(self):
        return self.status == 'published'

    @property
    def is_ready(self):
        """草稿是否已填好必填欄位，可以上架"""
        return bool(self.code and self.sizes)


class ProductImage(db.Model):
    __tablename__ = 'product_images'
    id          = db.Column(db.Integer, primary_key=True)
    product_id  = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    filename    = db.Column(db.String(255), nullable=False)
    is_primary  = db.Column(db.Boolean, default=False)
    order_index = db.Column(db.Integer, default=0)


class CartItem(db.Model):
    __tablename__ = 'cart_items'
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    size       = db.Column(db.String(10), nullable=False)
    color      = db.Column(db.String(50), nullable=True)   # 使用者選的顏色
    quantity   = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Order(db.Model):
    __tablename__ = 'orders'
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status     = db.Column(db.String(15), default='pending')  # 'pending'|'completed'|'cancelled'
    is_paid    = db.Column(db.Boolean, default=False)
    note       = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    items = db.relationship('OrderItem', backref='order', lazy=True,
                            cascade='all, delete-orphan')

    @property
    def total(self):
        return sum((i.price_at_order or 0) * i.quantity for i in self.items)

    @property
    def status_label(self):
        return {'pending': '待確認', 'completed': '完成', 'cancelled': '取消'}.get(self.status, self.status)


class OrderItem(db.Model):
    __tablename__ = 'order_items'
    id             = db.Column(db.Integer, primary_key=True)
    order_id       = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    product_id     = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=True)
    product_code   = db.Column(db.String(50))
    product_name   = db.Column(db.String(100))
    size           = db.Column(db.String(10), nullable=False)
    color          = db.Column(db.String(50), nullable=True)   # 快照顏色
    quantity       = db.Column(db.Integer, default=1)
    price_at_order = db.Column(db.Float, nullable=True)


# ─── 背單字模組 ──────────────────────────────────────────────────
class VocabProgress(db.Model):
    """記錄每位使用者對每個單字的學習進度"""
    __tablename__ = 'vocab_progress'
    id            = db.Column(db.Integer, primary_key=True)
    user_id       = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    word          = db.Column(db.String(100), nullable=False)   # 英文單字
    source        = db.Column(db.String(50), default='system', nullable=False) # 來源: 'system', 'group_1', etc.
    correct       = db.Column(db.Integer, default=0)            # 答對次數
    incorrect     = db.Column(db.Integer, default=0)            # 答錯次數
    last_reviewed = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('user_id', 'word', 'source', name='uq_user_word_source'),)

    @property
    def accuracy(self):
        total = self.correct + self.incorrect
        return round(self.correct / total * 100) if total > 0 else None


class VocabHistoryLog(db.Model):
    """記錄每次單字學習的詳細歷史（按次/天）"""
    __tablename__ = 'vocab_history_log'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    word = db.Column(db.String(100), nullable=False)
    source = db.Column(db.String(50), default='system', nullable=False)
    result = db.Column(db.String(20), nullable=False)   # 'correct' or 'incorrect'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ─── 學習群組模組 ──────────────────────────────────────────────────
class StudyGroup(db.Model):
    __tablename__ = 'study_groups'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    invite_code = db.Column(db.String(10), unique=True, nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    daily_goal = db.Column(db.Integer, default=10) # 每日背單字目標
    vocab_filter_config = db.Column(db.Text, nullable=True) # 單字漏斗設定 (JSON 格式)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class GroupMember(db.Model):
    __tablename__ = 'group_members'
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('study_groups.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

class GroupDailyRecord(db.Model):
    __tablename__ = 'group_daily_records'
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('study_groups.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.String(10), nullable=False) # YYYY-MM-DD
    words_studied = db.Column(db.Integer, default=0) # 當日已背數量
    quiz_score = db.Column(db.Integer, default=0) # 當日測驗分數 (最高分)
    quiz_taken = db.Column(db.Boolean, default=False) # 是否完成當日測驗

class GroupDailyAssignment(db.Model):
    __tablename__ = 'group_daily_assignments'
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('study_groups.id'), nullable=False)
    date = db.Column(db.String(10), nullable=False) # YYYY-MM-DD
    words_json = db.Column(db.Text, nullable=False) # JSON encoded list of word dicts: [{"word": "apple", "definition": "蘋果", ...}]

    __table_args__ = (db.UniqueConstraint('group_id', 'date', name='uq_group_date'),)
