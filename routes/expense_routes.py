from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from datetime import datetime

from services.expense_service import ExpenseService

expense_bp = Blueprint('expense', __name__, url_prefix='/expense')
expense_service = ExpenseService()

@expense_bp.route('/')
@login_required
def index():
    """本週期記帳"""
    start, end = expense_service.get_current_period()
    return render_template('expense/dashboard.html', start_date=start, end_date=end)

@expense_bp.route('/today')
@login_required
def today():
    """本日記帳"""
    settings = expense_service.get_settings()
    
    # Pre-process JSON fields for the template
    try:
        import json
        custom_categories = json.loads(settings.get('custom_categories') or '[]')
    except:
        custom_categories = []
        
    try:
        quick_shortcuts = json.loads(settings.get('quick_shortcuts') or '[]')
    except:
        quick_shortcuts = []
        
    return render_template('expense/today.html', 
                         custom_categories=custom_categories,
                         quick_shortcuts=quick_shortcuts)


@expense_bp.route('/history')
@login_required
def history():
    return render_template('expense/history.html')

@expense_bp.route('/settings')
@login_required
def settings():
    settings = expense_service.get_settings()
    return render_template('expense/settings.html', settings=settings)


@expense_bp.route('/api/records/grouped', methods=['GET'])
@login_required
def get_grouped_records():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if not start_date or not end_date:
        start_date, end_date = expense_service.get_current_period()
        
    summary = expense_service.get_grouped_summary(start_date, end_date)
    return jsonify(summary)

@expense_bp.route('/api/records', methods=['GET'])
@login_required
def get_records():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if not start_date or not end_date:
        start_date, end_date = expense_service.get_current_period()
        
    summary = expense_service.get_summary(start_date, end_date)
    return jsonify(summary)

@expense_bp.route('/api/records', methods=['POST'])
@login_required
def add_record():
    data = request.json
    if not data or 'amount' not in data:
        return jsonify({"error": "Missing data"}), 400
    
    # Default category emoji mapping help
    categories = {
        "飲食": "🍽️ 飲食",
        "衣著": "👕 衣著",
        "居住": "🏠 居住",
        "交通": "🚌 交通",
        "教育": "📖 教育",
        "娛樂": "🎮 娛樂",
        "其他": "📦 其他"
    }
    
    if data.get('category') in categories:
        data['category'] = categories[data['category']]
    
    record = expense_service.add_record(data)
    return jsonify(record), 201

@expense_bp.route('/api/records/<record_id>', methods=['PUT', 'DELETE'])
@login_required
def handle_record(record_id):
    if request.method == 'DELETE':
        if expense_service.delete_record(record_id):
            return '', 204
        return jsonify({"error": "Not found"}), 404
    
    data = request.json
    record = expense_service.update_record(record_id, data)
    if record:
        return jsonify(record)
    return jsonify({"error": "Not found"}), 404

@expense_bp.route('/api/history/periods')
@login_required
def get_periods():
    periods = expense_service.get_monthly_periods()
    return jsonify(periods)

@expense_bp.route('/api/settings', methods=['GET', 'POST'])
@login_required
def handle_settings():
    if request.method == 'POST':
        data = request.json
        settings = expense_service.update_settings(data)
        return jsonify(settings)
    
    settings = expense_service.get_settings()
    return jsonify(settings)
@expense_bp.route('/api/records/export', methods=['GET'])
@login_required
def export_records():
    from flask_login import current_user
    from services.email_service import EmailService
    from flask import Response
    
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if not start_date or not end_date:
        return jsonify({"error": "Missing dates"}), 400
        
    csv_data = expense_service.export_records_csv(start_date, end_date)
    filename = f"expense_export_{start_date}_{end_date}.csv"
    
    # Parse Notification Methods
    try:
        import json
        methods = json.loads(current_user.settings.notification_methods or '["download"]')
    except:
        methods = ['download']

    # 1. Email
    if 'email' in methods and current_user.email:
        # Get full data for email rendering
        summary_data = expense_service.get_summary(start_date, end_date)
        records = summary_data['records']
        
        # Calculate category stats for the email
        category_stats = {}
        for r in records:
            cat = r.get('category', '其他')
            cat_name = cat.split(' ')[1] if ' ' in cat else cat
            category_stats[cat_name] = category_stats.get(cat_name, 0) + r['amount']
            
        # Simplified top 5 categories
        top_categories = sorted(category_stats.items(), key=lambda x: x[1], reverse=True)[:5]
        
        try:
            EmailService.send_email(
                to=current_user.email,
                subject=f'記帳明細報表 ({start_date} - {end_date})',
                template='email/expense_export.html',
                username=current_user.username,
                period=f"{start_date} ~ {end_date}",
                total_amount=f"${summary_data.get('total_amount', 0):,}",
                records=records,
                top_categories=top_categories
            )
        except Exception as e:
            print(f"Email Error: {e}")

    # 2. LINE
    sent_nicknames = []
    if 'line' in methods:
        from services.line_service import LineService
        summary_data = expense_service.get_summary(start_date, end_date)
        total = summary_data.get('total_amount', 0)
        
        # Calculate stats
        from collections import defaultdict
        category_stats = defaultdict(lambda: {'count': 0, 'amount': 0, 'emoji': '📦'})
        
        records = summary_data.get('records', [])
        for r in records:
            cat_full = r.get('category', '其他')
            parts = cat_full.split(' ')
            if len(parts) > 1:
                emoji = parts[0]
                cat_name = parts[1]
            else:
                emoji = '📦' # Fallback emoji if no space
                cat_name = cat_full
                
            category_stats[cat_name]['count'] += 1
            category_stats[cat_name]['amount'] += int(r['amount'])
            category_stats[cat_name]['emoji'] = emoji

        msg = (
            f"📉 [記帳匯出通知] {current_user.username}\n"
            f"期間: {start_date} ~ {end_date}\n"
            f"總支出: ${total:,}\n"
            f"匯出時間: {datetime.now().strftime('%Y/%m/%d %H:%M')}\n"
            f"------------------\n"
        )
        
        # Add Category summary
        msg += "【各分類統計】\n"
        for cat_name, stats in sorted(category_stats.items(), key=lambda x: x[1]['amount'], reverse=True):
            msg += f"{stats['emoji']} {cat_name}: ${stats['amount']:,} ({stats['count']}筆)\n"
            
        msg += "------------------\n"
        
        # Add details
        msg += "【明細紀錄】\n"
        detail_lines = []
        for r in records:
            cat = r.get('category', '其他').split(' ')[0] # Get emoji or just first part
            detail_lines.append(f"{r['timestamp'][5:16]} {cat} ${int(r['amount'])}")
            
        msg += "\n".join(detail_lines)
            
        sent_nicknames = LineService.push_to_user(current_user.id, msg, module='expense')
            
    msg_text = f"報表（{start_date} ~ {end_date}）處理完成！"
    if sent_nicknames:
        msg_text += f"\n📲 已發送 LINE 至: {', '.join(sent_nicknames)}"
    if 'email' in methods and current_user.email:
        msg_text += f"\n📧 已發送 Email 至: {current_user.email}"
        
    response_data = {
        "success": True, 
        "message": msg_text
    }
    
    if 'download' in methods or not methods:
        response_data["csv_content"] = csv_data
        response_data["filename"] = filename
        if not methods:
            response_data["message"] = "檔案已下載"

    return jsonify(response_data)

@expense_bp.route('/api/expense-trend')
@login_required
def get_expense_trend():
    """
    回傳所有歷史帳單週期的支出趨勢
    從第一筆記錄到現在
    """
    from datetime import datetime, timedelta
    from dateutil.relativedelta import relativedelta
    from sqlalchemy import func
    from models import db, ExpenseRecord
    from flask_login import current_user
    
    settings = expense_service.get_settings()
    start_day = settings.get('billing_cycle_start_day', 10)
    
    # 找出第一筆記錄
    first_record = db.session.query(func.min(ExpenseRecord.timestamp))\
        .filter_by(user_id=current_user.id).scalar()
    
    if not first_record:
        return jsonify({"labels": [], "period_details": [], "data": [], "total_cycles": 0})
    
    # 從第一筆記錄的帳單週期開始
    first_date = datetime.strptime(first_record[:10], '%Y-%m-%d')
    
    # 找到第一個週期的開始日
    if first_date.day >= start_day:
        cycle_start = first_date.replace(day=start_day)
    else:
        cycle_start = (first_date - relativedelta(months=1)).replace(day=start_day)
    
    # 計算到現在
    today = datetime.now()
    if today.day >= start_day:
        current_cycle = today.replace(day=start_day)
    else:
        current_cycle = (today - relativedelta(months=1)).replace(day=start_day)
    
    labels = []
    period_details = []
    data = []
    current = cycle_start
    
    while current <= current_cycle:
        period_start = current.strftime('%Y-%m-%d')
        next_cycle = current + relativedelta(months=1)
        period_end = (next_cycle - timedelta(days=1)).strftime('%Y-%m-%d')
        
        # 查詢該週期支出
        summary = expense_service.get_summary(period_start, period_end, current_user)
        total = summary.get('total_amount', 0)
        
        labels.append(f"{current.strftime('%Y-%m')} 週期")
        period_details.append(f"{period_start} ~ {period_end}")
        data.append(float(total))
        
        current = next_cycle
    
    return jsonify({
        "labels": labels,
        "period_details": period_details,
        "data": data,
        "total_cycles": len(labels)
    })
