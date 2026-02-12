from models import db, ExpenseRecord, UserSettings
from flask_login import current_user
from datetime import datetime, timedelta
from sqlalchemy import func
import json

class ExpenseService:
    def _ensure_file_exists(self):
        # Deprecated: DB handles this
        pass

    def get_all_records(self):
        if not current_user.is_authenticated:
            return []
        records = ExpenseRecord.query.filter_by(user_id=current_user.id).order_by(ExpenseRecord.timestamp.desc()).all()
        return [self._to_dict(r) for r in records]

    def add_record(self, record_data):
        if not current_user.is_authenticated:
            return None
            
        new_record = ExpenseRecord(
            user_id=current_user.id,
            category=record_data.get('category'),
            note=record_data.get('note')
        )
        
        # Timestamp
        if 'timestamp' in record_data:
            new_record.timestamp = record_data['timestamp']
        else:
            new_record.timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
        # Amount
        try:
            new_record.amount = max(0.0, float(record_data.get('amount', 0.0)))
        except:
            new_record.amount = 0.0
            
        db.session.add(new_record)
        db.session.commit()
        return self._to_dict(new_record)

    def update_record(self, record_id, record_data):
        if not current_user.is_authenticated:
            return None
            
        record = ExpenseRecord.query.filter_by(id=record_id, user_id=current_user.id).first()
        if not record:
            return None
            
        if 'category' in record_data: record.category = record_data['category']
        if 'note' in record_data: record.note = record_data['note']
        if 'timestamp' in record_data: record.timestamp = record_data['timestamp']
        
        if 'amount' in record_data:
            try:
                record.amount = max(0.0, float(record_data['amount']))
            except:
                pass
                
        db.session.commit()
        return self._to_dict(record)

    def delete_record(self, record_id):
        if not current_user.is_authenticated:
            return False
            
        record = ExpenseRecord.query.filter_by(id=record_id, user_id=current_user.id).first()
        if record:
            db.session.delete(record)
            db.session.commit()
            return True
        return False

    def get_summary(self, start_date_str, end_date_str, user=None):
        target_user = user or current_user
        if hasattr(target_user, 'is_authenticated') and not target_user.is_authenticated and not user:
             return {"records": [], "total_amount": 0, "category_split": {}}
        if not target_user:
             return {"records": [], "total_amount": 0, "category_split": {}}
             
        # Filter: timestamp string comparison works for YYYY-MM-DD format if dates are YYYY-MM-DD
        # But timestamps are YYYY-MM-DD HH:MM:SS
        # start_date_str is YYYY-MM-DD
        
        records = ExpenseRecord.query.filter_by(user_id=target_user.id)\
            .filter(ExpenseRecord.timestamp >= start_date_str)\
            .filter(ExpenseRecord.timestamp < end_date_str + " 23:59:59")\
            .order_by(ExpenseRecord.timestamp.desc())\
            .all()
            
        # Refine filter logic to strictly match date prefix
        filtered = []
        total = 0
        categories = {}
        
        for r in records:
            rec_date = r.timestamp[:10]
            if start_date_str <= rec_date < end_date_str:
                filtered.append(self._to_dict(r))
                total += r.amount
                cat = r.category or '其他'
                categories[cat] = categories.get(cat, 0) + r.amount
                
        return {
            "records": filtered,
            "total_amount": total,
            "category_split": categories,
            "period": {"start": start_date_str, "end": end_date_str}
        }

    def get_grouped_summary(self, start_date_str, end_date_str):
        summary_data = self.get_summary(start_date_str, end_date_str)
        records = summary_data['records']
        
        def get_week_start(date_obj):
            return date_obj - timedelta(days=date_obj.weekday())

        weeks_grouped = {}
        
        for r in records:
            dt = datetime.strptime(r['timestamp'][:10], '%Y-%m-%d')
            wk_start = get_week_start(dt).strftime('%Y-%m-%d')
            day_str = dt.strftime('%Y-%m-%d')
            
            if wk_start not in weeks_grouped:
                weeks_grouped[wk_start] = {
                    "week_start": wk_start,
                    "total": 0,
                    "days": {}
                }
            
            weeks_grouped[wk_start]['total'] += r['amount']
            
            if day_str not in weeks_grouped[wk_start]['days']:
                weeks_grouped[wk_start]['days'][day_str] = {
                    "date": day_str,
                    "total": 0,
                    "records_count": 0
                }
            
            weeks_grouped[wk_start]['days'][day_str]['total'] += r['amount']
            weeks_grouped[wk_start]['days'][day_str]['records_count'] += 1

        sorted_weeks = []
        for ws in sorted(weeks_grouped.keys(), reverse=True):
            w_data = weeks_grouped[ws]
            ws_dt = datetime.strptime(ws, '%Y-%m-%d')
            we_dt = ws_dt + timedelta(days=6)
            w_data['week_end'] = we_dt.strftime('%Y-%m-%d')
            
            sorted_days = []
            for ds in sorted(w_data['days'].keys(), reverse=True):
                sorted_days.append(w_data['days'][ds])
            
            w_data['days'] = sorted_days
            sorted_weeks.append(w_data)

        now = datetime.now()
        this_wk_start = (now - timedelta(days=now.weekday())).strftime('%Y-%m-%d')
        this_wk_end = (now - timedelta(days=now.weekday()) + timedelta(days=6)).strftime('%Y-%m-%d')

        return {
            "weeks": sorted_weeks,
            "total_amount": summary_data['total_amount'],
            "period": summary_data['period'],
            "this_week_range": {"start": this_wk_start, "end": this_wk_end}
        }

    def get_current_period(self):
        now = datetime.now()
        # Start: 1st day of current month
        start_date = datetime(now.year, now.month, 1)
        
        # End: Last day of current month
        # Logic: First day of next month - 1 day
        if now.month == 12:
            next_month = datetime(now.year + 1, 1, 1)
        else:
            next_month = datetime(now.year, now.month + 1, 1)
            
        end_date = next_month - timedelta(days=1)
            
        return start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')

    def get_settings(self):
        if not current_user.is_authenticated:
            return {"monthly_budget": 10000}
            
        settings = current_user.settings
        if not settings:
            settings = UserSettings(user_id=current_user.id)
            db.session.add(settings)
            db.session.commit()
            
        # Ensure fresh data
        db.session.expire(settings)
        db.session.refresh(settings)
            
        return {
            "monthly_budget": settings.monthly_budget,
            "editable_month_range": settings.editable_month_range,
            "budget_alert_threshold": settings.budget_alert_threshold,
            "billing_cycle_start_day": settings.billing_cycle_start_day,
            "custom_categories": settings.custom_categories,
            "recurring_expenses": settings.recurring_expenses,
            "quick_shortcuts": settings.quick_shortcuts
        }

    def update_settings(self, settings_data):
        if not current_user.is_authenticated:
            return {}
            
        if 'monthly_budget' in settings_data:
            try:
                current_user.settings.monthly_budget = float(settings_data['monthly_budget'])
            except: pass
            
        if 'editable_month_range' in settings_data:
            try:
                current_user.settings.editable_month_range = int(settings_data['editable_month_range'])
            except: pass
            
        if 'budget_alert_threshold' in settings_data:
            try:
                current_user.settings.budget_alert_threshold = int(settings_data['budget_alert_threshold'])
            except: pass

        if 'billing_cycle_start_day' in settings_data:
            try:
                current_user.settings.billing_cycle_start_day = int(settings_data['billing_cycle_start_day'])
            except: pass
            
        if 'custom_categories' in settings_data:
            current_user.settings.custom_categories = json.dumps(settings_data['custom_categories'], ensure_ascii=False)
            
        if 'recurring_expenses' in settings_data:
            current_user.settings.recurring_expenses = json.dumps(settings_data['recurring_expenses'], ensure_ascii=False)
            
        if 'quick_shortcuts' in settings_data:
            current_user.settings.quick_shortcuts = json.dumps(settings_data['quick_shortcuts'], ensure_ascii=False)
            
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e
        return self.get_settings()

    def get_monthly_periods(self):
        if not current_user.is_authenticated:
             return []
             
        # Find min and max date
        result = db.session.query(
             func.min(ExpenseRecord.timestamp), 
             func.max(ExpenseRecord.timestamp)
        ).filter_by(user_id=current_user.id).first()

        if not result or not result[0]:
            start, end = self.get_current_period()
            return [{"label": f"{start} ~ {end}", "start": start, "end": end}]

        # Use first record date to find the first month start
        first_date = datetime.strptime(result[0][:10], '%Y-%m-%d')
        current = datetime(first_date.year, first_date.month, 1)

        periods = []
        now = datetime.now()
        # Final cutoff is end of this month
        if now.month == 12:
            next_m = datetime(now.year + 1, 1, 1)
        else:
            next_m = datetime(now.year, now.month + 1, 1)
        final_cutoff = next_m - timedelta(days=1)


        while current <= final_cutoff:
            # Find end of month
            if current.month == 12:
                next_month_start = datetime(current.year + 1, 1, 1)
            else:
                next_month_start = datetime(current.year, current.month + 1, 1)
            
            p_end_dt = next_month_start - timedelta(days=1)
            p_start = current.strftime('%Y-%m-%d')
            p_end = p_end_dt.strftime('%Y-%m-%d')
            
            periods.append({
                "label": f"{p_start} ~ {p_end}",
                "start": p_start,
                "end": p_end
            })
            current = next_month_start

        return periods
        
    def export_records_csv(self, start_date, end_date):
        import io
        import csv
        
        filtered = self.get_summary(start_date, end_date)['records']
        
        output = io.StringIO()
        output.write('\ufeff')
        
        writer = csv.writer(output)
        writer.writerow(['日期時間', '類別', '項目名稱', '金額'])
        
        for r in filtered:
            writer.writerow([
                r.get('timestamp', ''),
                r.get('category', '其他'),
                r.get('note', ''),
                r.get('amount', 0)
            ])
            
        return output.getvalue()

    def _to_dict(self, record):
        return {
            'id': record.id,
            'timestamp': record.timestamp,
            'category': record.category,
            'note': record.note,
            'amount': record.amount
        }
