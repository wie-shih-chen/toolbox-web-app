from flask import Blueprint, render_template, request, jsonify, Response
from flask_login import login_required, current_user
from services.salary_service import SalaryService
from models import db, SalaryRecord, UserSettings, Company, CompanyShiftReminder
from datetime import datetime, timedelta
import calendar
import json

salary_bp = Blueprint('salary', __name__)
service = SalaryService()

# ================= COMPANY API =================

@salary_bp.route('/api/companies', methods=['GET'])
@login_required
def get_companies():
    companies = Company.query.filter_by(user_id=current_user.id, is_active=True)\
        .order_by(Company.created_at.asc()).all()
    result = []
    for c in companies:
        reminders = CompanyShiftReminder.query.filter_by(company_id=c.id, is_active=True).all()
        shift_reminders = [{
            'id': r.id,
            'offset_minutes': r.offset_minutes,
            'message_template': r.message_template
        } for r in reminders]
        
        result.append({
            'id': c.id,
            'name': c.name,
            'color': c.color,
            'hourly_rate': c.hourly_rate,
            'notify_payday_enabled': c.notify_payday_enabled,
            'notify_payday_day': c.notify_payday_day,
            'notify_payday_time': c.notify_payday_time,
            'notify_weekly_enabled': c.notify_weekly_enabled,
            'notify_weekly_day': c.notify_weekly_day,
            'notify_weekly_time': c.notify_weekly_time,
            'shift_reminders': shift_reminders,
            'break_rules': c.break_rules or '[]'
        })
    return jsonify(result)

@salary_bp.route('/api/companies', methods=['POST'])
@login_required
def create_company():
    data = request.json or {}
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'error': '公司名稱不能為空'}), 400

    company = Company(
        user_id=current_user.id,
        name=name,
        color=data.get('color', '#6366f1'),
        hourly_rate=float(data.get('hourly_rate', current_user.settings.hourly_rate or 183.0)),
        notify_payday_enabled=bool(data.get('notify_payday_enabled', False)),
        notify_payday_day=int(data.get('notify_payday_day', 10)),
        notify_payday_time=data.get('notify_payday_time', '09:00'),
        notify_weekly_enabled=bool(data.get('notify_weekly_enabled', False)),
        notify_weekly_day=data.get('notify_weekly_day', 'sunday'),
        notify_weekly_time=data.get('notify_weekly_time', '20:00'),
        break_rules=data.get('break_rules', '[]')
    )
    db.session.add(company)
    db.session.commit()
    return jsonify({'id': company.id, 'name': company.name, 'color': company.color}), 201

@salary_bp.route('/api/companies/<int:company_id>', methods=['PUT'])
@login_required
def update_company(company_id):
    company = Company.query.filter_by(id=company_id, user_id=current_user.id).first()
    if not company:
        return jsonify({'error': 'Not found'}), 404
    data = request.json or {}
    if 'name' in data: company.name = data['name'].strip()
    if 'color' in data: company.color = data['color']
    if 'hourly_rate' in data: company.hourly_rate = float(data['hourly_rate'])
    if 'notify_payday_enabled' in data: company.notify_payday_enabled = bool(data['notify_payday_enabled'])
    if 'notify_payday_day' in data: company.notify_payday_day = int(data['notify_payday_day'])
    if 'notify_payday_time' in data: company.notify_payday_time = data['notify_payday_time']
    if 'notify_weekly_enabled' in data: company.notify_weekly_enabled = bool(data['notify_weekly_enabled'])
    if 'notify_weekly_day' in data: company.notify_weekly_day = data['notify_weekly_day']
    if 'notify_weekly_time' in data: company.notify_weekly_time = data['notify_weekly_time']
    if 'break_rules' in data: company.break_rules = data['break_rules']
    
    if 'shift_reminders' in data:
        # First, deactivate all existing active reminders for this company
        existing_reminders = CompanyShiftReminder.query.filter_by(company_id=company.id, is_active=True).all()
        for r in existing_reminders:
            r.is_active = False
            
        # Add the new ones
        for rem_data in data['shift_reminders']:
            new_reminder = CompanyShiftReminder(
                company_id=company.id,
                offset_minutes=int(rem_data.get('offset_minutes', 0)),
                message_template=rem_data.get('message_template', '記得打卡！'),
                is_active=True
            )
            db.session.add(new_reminder)

    db.session.commit()
    return jsonify({'success': True})

@salary_bp.route('/api/companies/<int:company_id>', methods=['DELETE'])
@login_required
def delete_company(company_id):
    company = Company.query.filter_by(id=company_id, user_id=current_user.id).first()
    if not company:
        return jsonify({'error': 'Not found'}), 404
        
    action = request.args.get('action')
    record_count = SalaryRecord.query.filter_by(company_id=company_id).count()
    
    if record_count > 0:
        if action == 'hide':
            pass
        elif action == 'delete_all':
            SalaryRecord.query.filter_by(company_id=company_id).delete()
        else:
            return jsonify({'error': f'此公司有 {record_count} 筆班表記錄，請先將記錄重新歸屬或刪除後再刪除公司', 'record_count': record_count}), 400
            
    company.is_active = False  # Soft delete
    db.session.commit()
    return jsonify({'success': True})

@salary_bp.route('/api/companies/assign-legacy', methods=['POST'])
@login_required
def assign_legacy_records():
    """批次將 company_id=NULL 的舊記錄歸屬到指定公司"""
    data = request.json or {}
    company_id = data.get('company_id')
    if not company_id:
        return jsonify({'error': '請指定公司'}), 400
    company = Company.query.filter_by(id=company_id, user_id=current_user.id).first()
    if not company:
        return jsonify({'error': '找不到公司'}), 404
        
    records = SalaryRecord.query.filter_by(user_id=current_user.id, company_id=None).all()
    count = len(records)
    for r in records:
        r.company_id = company_id
    db.session.commit()
    
    return jsonify({'success': True, 'assigned_count': count})

@salary_bp.route('/api/companies/legacy-count', methods=['GET'])
@login_required
def get_legacy_count():
    """回傳尚未歸屬公司的記錄數量"""
    count = SalaryRecord.query.filter_by(user_id=current_user.id, company_id=None).count()
    return jsonify({'count': count})

@salary_bp.route('/api/companies/summary', methods=['GET'])
@login_required
def get_companies_summary():
    """各公司本月收入 + 時數統計"""
    from datetime import date
    today = date.today()
    start = today.replace(day=1).strftime('%Y-%m-%d')
    import calendar
    last_day = calendar.monthrange(today.year, today.month)[1]
    end = today.replace(day=last_day).strftime('%Y-%m-%d')

    companies = Company.query.filter_by(user_id=current_user.id, is_active=True).all()
    result = []
    for c in companies:
        records = SalaryRecord.query.filter(
            SalaryRecord.user_id == current_user.id,
            SalaryRecord.company_id == c.id,
            SalaryRecord.date >= start,
            SalaryRecord.date <= end
        ).all()
        total_amount = sum(r.amount for r in records)
        total_hours = sum(r.hours or 0 for r in records if r.type == 'shift')
        result.append({
            'company_id': c.id,
            'name': c.name,
            'color': c.color,
            'total_amount': total_amount,
            'total_hours': round(total_hours, 1),
            'record_count': len(records)
        })
    return jsonify(result)


@salary_bp.route('/')
@login_required
def index():
    # Lazy Automation: Check if monthly report needs sending
    # Wrapped in try-except to ensures dashboard NEVER crashes due to background tasks
    try:
        from services.report_service import ReportService
        ReportService.check_and_send_pending_reports(current_user)
    except Exception as e:
        print(f"Lazy Report Error: {e}")

    # Default to current week
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    date_str = monday.strftime('%Y-%m-%d')
    return render_template('salary/dashboard.html', start_date=date_str)

@salary_bp.route('/monthly')
@login_required
def monthly():
    return render_template('salary/monthly.html')

@salary_bp.route('/history')
@login_required
def history():
    return render_template('salary/history.html')

@salary_bp.route('/settings')
@login_required
def settings():
    current_settings = service.get_settings()
    return render_template('salary/settings.html', settings=current_settings)

@salary_bp.route('/notifications')
@login_required
def notifications():
    return render_template('salary/notifications.html')

# ================= MAX API =================

@salary_bp.route('/api/records', methods=['GET'])
@login_required
def get_records():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if start_date and end_date:
        records = service.get_records_by_range(start_date, end_date)
    else:
        records = service.get_all_records()
        
    return jsonify(records)

@salary_bp.route('/api/records', methods=['POST'])
@login_required
def add_record():
    data = request.json
    try:
        new_record = service.add_record(data)
        return jsonify(new_record), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@salary_bp.route('/api/records/<record_id>', methods=['PUT'])
@login_required
def update_record(record_id):
    data = request.json
    try:
        updated_record = service.update_record(record_id, data)
        if updated_record:
            return jsonify(updated_record)
        return jsonify({'error': 'Record not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@salary_bp.route('/api/records/<record_id>', methods=['DELETE'])
@login_required
def delete_record(record_id):
    if service.delete_record(record_id):
        return jsonify({'success': True})
    return jsonify({'error': 'Record not found'}), 404

@salary_bp.route('/api/stats', methods=['GET'])
@login_required
def get_stats():
    start_date = request.args.get('start_date')
    summary = service.calculate_weekly_summary(start_date)
    return jsonify(summary)

@salary_bp.route('/api/holidays', methods=['GET'])
@login_required
def get_holidays():
    """Return Taiwan national holidays for a given year as {YYYY-MM-DD: name}."""
    try:
        year = int(request.args.get('year', datetime.now().year))
    except (ValueError, TypeError):
        year = datetime.now().year
    try:
        from services.tw_holidays import get_holidays as _get
        return jsonify(_get(year))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@salary_bp.route('/api/settings', methods=['GET', 'POST'])
@login_required
def handle_settings():
    if request.method == 'POST':
        data = request.json
        updated = service.update_settings(data)
        return jsonify(updated)
    return jsonify(service.get_settings())

@salary_bp.route('/api/actions/copy_week', methods=['POST'])
@login_required
def copy_week():
    target_date = request.json.get('target_date') # The Monday of current week
    if not target_date:
        return jsonify({'error': 'No target date'}), 400
        
    count = service.copy_week_records(target_date)
    return jsonify({'count': count})

@salary_bp.route('/api/actions/clear_week', methods=['POST'])
@login_required
def clear_week():
    week_start = request.json.get('week_start')
    if not week_start:
        return jsonify({'error': 'No week start'}), 400
        
    count = service.clear_week_records(week_start)
    return jsonify({'count': count})

@salary_bp.route('/api/export', methods=['GET'])
@login_required
def export_csv():
    from flask_login import current_user
    from services.email_service import EmailService
    
    csv_content = service.generate_csv_export()
    filename = f"salary_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    # Parse Notification Methods
    try:
        import json
        methods = json.loads(current_user.settings.notification_methods or '["download"]')
    except:
        methods = ['download']

    # 1. Email
    if 'email' in methods and current_user.email:
        # Get stats for email
        records = service.get_all_records()
        records.sort(key=lambda x: x['date'], reverse=True)
        total_amount = sum(r.get('amount', 0) for r in records)
        export_date = datetime.now().strftime('%Y/%m/%d %H:%M')
        
        try:
            EmailService.send_email(
                to=current_user.email,
                subject=f'薪資排班報表 - {export_date}',
                template='email/salary_export.html',
                username=current_user.username,
                record_count=len(records),
                export_date=export_date,
                total_amount=f"${total_amount:,}",
                records=records
            )
        except Exception as e:
            print(f"Email Error: {e}")

    sent_nicknames = []
    # 2. LINE
    if 'line' in methods:
        from services.line_service import LineService
        records = service.get_all_records()
        total_amount = sum(r.get('amount', 0) for r in records)
        
        # Calculate stats
        from collections import defaultdict
        type_stats = defaultdict(lambda: {'count': 0, 'amount': 0, 'hours': 0})
        
        for r in records:
            rtype = "排班" if r['type'] == 'shift' else "獎金"
            if r['type'] != 'shift' and r['type'] != 'bonus':
                rtype = r['type'] # Fallback
            type_stats[rtype]['count'] += 1
            type_stats[rtype]['amount'] += r.get('amount', 0)
            if r['type'] == 'shift':
                type_stats[rtype]['hours'] += r.get('hours', 0)

        from services.notification_service import NotificationTemplate
        msg = NotificationTemplate.get_salary_export_msg(
            username=current_user.username,
            records=records,
            total_amount=total_amount,
            type_stats=type_stats
        )
            
        sent_nicknames = LineService.push_to_user(current_user.id, msg, module='salary')

    msg_text = "報表處理完成！"
    if sent_nicknames:
        msg_text += f"\n📲 已發送 LINE 至: {', '.join(sent_nicknames)}"
    if 'email' in methods and current_user.email:
        msg_text += f"\n📧 已發送 Email 至: {current_user.email}"
        
    response_data = {
        "success": True, 
        "message": msg_text
    }
    
    if 'download' in methods or not methods:
        response_data["csv_content"] = csv_content
        response_data["filename"] = filename
        if not methods:
            response_data["message"] = "檔案已下載"

    return jsonify(response_data)

@salary_bp.route('/api/export-period', methods=['GET'])
@login_required
def export_period_csv():
    """
    匯出指定月份週期的 CSV。
    期望參數: ?period=YYYY-MM（e.g. 2026-03）
    """
    from flask_login import current_user
    from services.email_service import EmailService
    import calendar as cal_module

    period = request.args.get('period', '')  # e.g. '2026-03'
    try:
        year, month = int(period[:4]), int(period[5:7])
    except (ValueError, IndexError):
        return jsonify({'error': '無效的週期格式，請提供 YYYY-MM'}), 400

    last_day = cal_module.monthrange(year, month)[1]
    start_date = f"{year:04d}-{month:02d}-01"
    end_date   = f"{year:04d}-{month:02d}-{last_day:02d}"

    records = service.get_records_by_range(start_date, end_date)
    if not records:
        return jsonify({'error': f'{period} 該週期無資料'}), 404

    records.sort(key=lambda x: x['date'])
    total_amount = sum(r.get('amount', 0) for r in records)

    # Build CSV
    lines = ['日期,類型,開始時間,結束時間,時數,時薪,金額,備註']
    for r in records:
        note = (r.get('note') or '').replace(',', '，')
        lines.append(
            f"{r['date']},"
            f"{'排班' if r['type']=='shift' else '獎金'},"
            f"{r.get('start_time','') or ''},"
            f"{r.get('end_time','') or ''},"
            f"{r.get('hours','')},"
            f"{r.get('rate','')},"
            f"{r.get('amount','')},"
            f"{note}"
        )
    lines.append(f"合計,,,,,${total_amount:,}")
    csv_content = '\n'.join(lines)
    filename = f"salary_{period}.csv"

    # Parse notification methods
    try:
        import json
        methods = json.loads(current_user.settings.notification_methods or '["download"]')
    except:
        methods = ['download']

    # Email
    if 'email' in methods and current_user.email:
        export_date = datetime.now().strftime('%Y/%m/%d %H:%M')
        try:
            EmailService.send_email(
                to=current_user.email,
                subject=f'薪資排班報表（{start_date} ~ {end_date}）- {export_date}',
                template='email/salary_export.html',
                username=current_user.username,
                record_count=len(records),
                export_date=export_date,
                total_amount=f"${total_amount:,}",
                records=records
            )
        except Exception as e:
            print(f"Email Error: {e}")

    # LINE
    sent_nicknames = []
    if 'line' in methods:
        from services.line_service import LineService
        # Calculate stats
        from collections import defaultdict
        type_stats = defaultdict(lambda: {'count': 0, 'amount': 0, 'hours': 0})
        
        for r in records:
            rtype = '排班' if r['type'] == 'shift' else '獎金'
            type_stats[rtype]['count'] += 1
            type_stats[rtype]['amount'] += r.get('amount', 0)
            if r['type'] == 'shift':
                type_stats[rtype]['hours'] += r.get('hours', 0)

        from services.notification_service import NotificationTemplate
        msg = NotificationTemplate.get_salary_export_msg(
            username=current_user.username,
            records=records,
            total_amount=total_amount,
            type_stats=type_stats,
            start_date=start_date,
            end_date=end_date
        )
        try:
            sent_nicknames = LineService.push_to_user(current_user.id, msg, module='salary')
        except Exception as e:
            print(f"LINE Error: {e}")

    msg_text = f"報表（{period}）處理完成！"
    if sent_nicknames:
        msg_text += f"\n📲 已發送 LINE 至: {', '.join(sent_nicknames)}"
    if 'email' in methods and current_user.email:
        msg_text += f"\n📧 已發送 Email 至: {current_user.email}"
        
    response_data = {
        "success": True, 
        "message": msg_text
    }
    
    if 'download' in methods or not methods:
        response_data["csv_content"] = csv_content
        response_data["filename"] = filename
        if not methods:
            response_data["message"] = "檔案已下載"

    return jsonify(response_data)

@salary_bp.route('/api/history/periods', methods=['GET'])
@login_required
def get_history_periods():
    periods = service.get_monthly_periods()
    return jsonify(periods)

@salary_bp.route('/api/history/data', methods=['GET'])
@login_required
def get_history_data():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if not start_date or not end_date:
        return jsonify({'error': 'Missing dates'}), 400
        
    data = service.get_history_summary(start_date, end_date)
    return jsonify(data)

@salary_bp.route('/api/income-trend')
@login_required
def get_income_trend():
    """
    回傳所有歷史月份的薪資收入趨勢
    從第一筆記錄到現在
    """
    from datetime import datetime, timedelta
    from dateutil.relativedelta import relativedelta
    from sqlalchemy import func
    from models import db, SalaryRecord
    
    # 找出第一筆記錄的日期
    first_record = db.session.query(func.min(SalaryRecord.date))\
        .filter_by(user_id=current_user.id).scalar()
    
    if not first_record:
        return jsonify({"labels": [], "data": [], "total_months": 0})
    
    # 從第一筆記錄的月份開始
    first_date = datetime.strptime(first_record, '%Y-%m-%d')
    start_month = first_date.replace(day=1)
    
    # 到當前月份
    today = datetime.now()
    end_month = today.replace(day=1)
    
    labels = []
    data = []
    company_details = []
    current = start_month
    
    while current <= end_month:
        # 月份範圍
        month_start = current.strftime('%Y-%m-%d')
        
        if current.month == 12:
            next_month = current.replace(year=current.year+1, month=1, day=1)
        else:
            next_month = current.replace(month=current.month+1, day=1)
        
        month_end = (next_month - timedelta(days=1)).strftime('%Y-%m-%d')
        
        # 查詢該月總收入
        summary = service.get_history_summary(month_start, month_end)
        total = summary.get('total_amount', 0)
        
        # 統計各公司收入
        companies = {}
        for r in summary.get('records', []):
            c_name = r.get('company_name') or '未指定公司'
            companies[c_name] = companies.get(c_name, 0) + float(r.get('amount', 0))
            
        labels.append(current.strftime('%Y-%m'))
        data.append(float(total))
        company_details.append(companies)
        
        current = next_month
    
    return jsonify({
        "labels": labels,
        "data": data,
        "company_details": company_details,
        "total_months": len(labels)
    })

