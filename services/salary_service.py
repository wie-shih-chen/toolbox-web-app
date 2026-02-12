from models import db, SalaryRecord, UserSettings
from flask_login import current_user
from datetime import datetime, timedelta
from sqlalchemy import func

class SalaryService:
    def get_all_records(self, user=None):
        target_user = user or current_user
        # Check if we have a valid user (either passed or logged in)
        if hasattr(target_user, 'is_authenticated') and not target_user.is_authenticated and not user:
            return []
        if not target_user:
            return []
            
        # Return dict representations to match expected format
        records = SalaryRecord.query.filter_by(user_id=target_user.id).order_by(SalaryRecord.date.asc()).all()
        return [self._to_dict(r) for r in records]

    def get_records_by_range(self, start_date_str, end_date_str, user=None):
        target_user = user or current_user
        if hasattr(target_user, 'is_authenticated') and not target_user.is_authenticated and not user:
            return []
        if not target_user:
            return []
            
        records = SalaryRecord.query.filter_by(user_id=target_user.id)\
            .filter(SalaryRecord.date >= start_date_str)\
            .filter(SalaryRecord.date <= end_date_str)\
            .order_by(SalaryRecord.date.asc(), SalaryRecord.start_time.asc())\
            .all()
            
        return [self._to_dict(r) for r in records]

    def _calculate_hours(self, start_time_str, end_time_str):
        try:
            start_dt = datetime.strptime(start_time_str, '%H:%M')
            end_dt = datetime.strptime(end_time_str, '%H:%M')
            
            if end_dt < start_dt:
                end_dt += timedelta(days=1)
                
            delta = end_dt - start_dt
            return delta.total_seconds() / 3600.0
        except (ValueError, TypeError):
            return 0.0

    def add_record(self, record_data):
        if not current_user.is_authenticated:
            return None
            
        new_record = SalaryRecord(
            user_id=current_user.id,
            date=record_data.get('date'),
            type=record_data.get('type'),
            note=record_data.get('note')
        )
        
        if new_record.type == 'shift':
            start_t = record_data.get('start_time')
            end_t = record_data.get('end_time')
            new_record.start_time = start_t
            new_record.end_time = end_t
            
            if start_t and end_t:
                new_record.hours = self._calculate_hours(start_t, end_t)
            
            # Rate handling
            raw_rate = record_data.get('rate')
            settings = self.get_settings()
            default_rate = float(settings.get('hourly_rate', 183.0))
            
            if not raw_rate:
                new_record.rate = default_rate
            else:
                try:
                    new_record.rate = float(raw_rate)
                except:
                    new_record.rate = default_rate
                    
            new_record.amount = int(new_record.hours * new_record.rate)
            
        else:
            # Bonus
            try:
                new_record.amount = int(record_data.get('amount', 0))
            except:
                new_record.amount = 0
                
            # Allow optional hours for bonus
            if 'hours' in record_data and record_data['hours']:
                try:
                    new_record.hours = float(record_data['hours'])
                except:
                    new_record.hours = 0.0
                
        db.session.add(new_record)
        db.session.commit()
        return self._to_dict(new_record)

    def update_record(self, record_id, record_data):
        if not current_user.is_authenticated:
            return None
            
        # Record ID in DB is int, but frontend might send string UUID (legacy) or int
        # For new DB records, it's int. For legacy compat during transition, we might need care, 
        # but since we migrated data to new table, we should use new IDs.
        # The frontend likely expects the ID it got from get_records.
        
        record = SalaryRecord.query.filter_by(id=record_id, user_id=current_user.id).first()
        if not record:
            return None
            
        if 'date' in record_data: record.date = record_data['date']
        if 'note' in record_data: record.note = record_data['note']
        
        if record.type == 'shift':
            if 'start_time' in record_data: record.start_time = record_data['start_time']
            if 'end_time' in record_data: record.end_time = record_data['end_time']
            
            if record.start_time and record.end_time:
                record.hours = self._calculate_hours(record.start_time, record.end_time)
                
            if 'rate' in record_data:
                try:
                    record.rate = float(record_data['rate'])
                except:
                    pass
            
            record.amount = int(record.hours * record.rate)
            
        else:
            if 'amount' in record_data:
                try:
                    record.amount = int(record_data['amount'])
                except:
                    pass

            if 'hours' in record_data:
                try:
                    val = record_data['hours']
                    record.hours = float(val) if val is not None and val != '' else 0.0
                except:
                    pass
                    
        db.session.commit()
        return self._to_dict(record)

    def delete_record(self, record_id):
        if not current_user.is_authenticated:
            return False
            
        record = SalaryRecord.query.filter_by(id=record_id, user_id=current_user.id).first()
        if record:
            db.session.delete(record)
            db.session.commit()
            return True
        return False

    def get_settings(self):
        if not current_user.is_authenticated:
             return {"hourly_rate": 183.0}
             
        settings = current_user.settings
        if not settings:
            # Create if missing
            settings = UserSettings(user_id=current_user.id)
            db.session.add(settings)
            db.session.commit()
            
        return {
             "hourly_rate": settings.hourly_rate,
            "editable_month_range": settings.editable_month_range,
            "default_start_time": settings.default_start_time,
            "default_end_time": settings.default_end_time,
            "target_income": settings.target_income,
            "billing_cycle_start_day": settings.billing_cycle_start_day,
            "custom_categories": settings.custom_categories,
            "recurring_expenses": settings.recurring_expenses
        }

    def update_settings(self, settings_data):
        if not current_user.is_authenticated:
            return {}
            
        if 'hourly_rate' in settings_data:
            try:
                current_user.settings.hourly_rate = float(settings_data['hourly_rate'])
            except: pass
            
        if 'editable_month_range' in settings_data:
            try:
                current_user.settings.editable_month_range = int(settings_data['editable_month_range'])
            except: pass

        if 'default_start_time' in settings_data:
            current_user.settings.default_start_time = settings_data['default_start_time']
            
        if 'default_end_time' in settings_data:
            current_user.settings.default_end_time = settings_data['default_end_time']
            
        if 'target_income' in settings_data:
            try:
                current_user.settings.target_income = int(settings_data['target_income'])
            except: pass
            
        if 'billing_cycle_start_day' in settings_data:
            try:
                current_user.settings.billing_cycle_start_day = int(settings_data['billing_cycle_start_day'])
            except: pass
            
        if 'custom_categories' in settings_data:
            current_user.settings.custom_categories = settings_data['custom_categories']
            
        if 'recurring_expenses' in settings_data:
            current_user.settings.recurring_expenses = settings_data['recurring_expenses']
            
        try:
            db.session.commit()
        except: pass
                
        return self.get_settings()

    def calculate_weekly_summary(self, start_date_str):
        start = datetime.strptime(start_date_str, '%Y-%m-%d')
        end = start + timedelta(days=6)
        end_str = end.strftime('%Y-%m-%d')
        
        records = self.get_records_by_range(start_date_str, end_str)
        
        total_hours = sum(r['hours'] for r in records if 'hours' in r)
        total_amount = sum(r['amount'] for r in records)
        
        return {
            "total_hours": total_hours,
            "total_amount": int(total_amount),
            "record_count": len(records)
        }

    def copy_week_records(self, target_week_start_str):
        if not current_user.is_authenticated:
            return 0
            
        target_start = datetime.strptime(target_week_start_str, '%Y-%m-%d')
        source_start = target_start - timedelta(days=7)
        source_end = source_start + timedelta(days=6)
        
        source_records = SalaryRecord.query.filter_by(user_id=current_user.id)\
            .filter(SalaryRecord.date >= source_start.strftime('%Y-%m-%d'))\
            .filter(SalaryRecord.date <= source_end.strftime('%Y-%m-%d'))\
            .all()
            
        if not source_records:
            return 0
            
        count = 0
        current_rate = current_user.settings.hourly_rate
        
        for r in source_records:
            old_date = datetime.strptime(r.date, '%Y-%m-%d')
            day_diff = (old_date - source_start).days
            new_date = target_start + timedelta(days=day_diff)
            
            new_record = SalaryRecord(
                user_id=current_user.id,
                date=new_date.strftime('%Y-%m-%d'),
                type=r.type,
                start_time=r.start_time,
                end_time=r.end_time,
                hours=r.hours,
                note=r.note
            )
            
            if r.type == 'shift':
                new_record.rate = current_rate
                new_record.amount = int(new_record.hours * current_rate)
            else:
                new_record.amount = r.amount
                
            db.session.add(new_record)
            count += 1
            
        db.session.commit()
        return count

    def clear_week_records(self, week_start_str):
        if not current_user.is_authenticated:
            return 0
            
        start = datetime.strptime(week_start_str, '%Y-%m-%d')
        end = start + timedelta(days=6)
        
        deleted = SalaryRecord.query.filter_by(user_id=current_user.id)\
            .filter(SalaryRecord.date >= start.strftime('%Y-%m-%d'))\
            .filter(SalaryRecord.date <= end.strftime('%Y-%m-%d'))\
            .delete()
            
        db.session.commit()
        return deleted

    def generate_csv_export(self):
        records = self.get_all_records()
        
        lines = ["日期,類型,開始時間,結束時間,時數,時薪/金額,備註"]
        total_hours = 0
        total_amount = 0
        
        for r in records:
            if r['type'] == 'shift':
                line = f"{r['date']},排班,{r.get('start_time','')},{r.get('end_time','')},{r.get('hours',0)},{r.get('rate',0)},{r.get('note','')}"
                total_hours += r.get('hours', 0)
            else:
                line = f"{r['date']},獎金,,,{r.get('hours', '')},{r['amount']},{r.get('note', '')}"
            
            total_amount += r['amount']
            lines.append(line)
        
        lines.append(f"總計,,,,{total_hours},{total_amount},")
        return "\n".join(lines)

    def get_monthly_periods(self):
        if not current_user.is_authenticated:
            return []
            
        # Find min and max date
        result = db.session.query(
            func.min(SalaryRecord.date), 
            func.max(SalaryRecord.date)
        ).filter_by(user_id=current_user.id).first()
        
        if not result or not result[0]:
            now = datetime.now()
            start_date = now - timedelta(days=30)
            end_date = now + timedelta(days=30)
        else:
            start_date = datetime.strptime(result[0], '%Y-%m-%d') - timedelta(days=30)
            end_date = datetime.strptime(result[1], '%Y-%m-%d') + timedelta(days=30)

        # Normalize to 1st of month
        current = datetime(start_date.year, start_date.month, 1)

        periods = []
        now = datetime.now()
        final_date = end_date if end_date > now else now
        
        while current <= final_date:
            # Next month start
            if current.month == 12:
                next_month = datetime(current.year + 1, 1, 1)
            else:
                next_month = datetime(current.year, current.month + 1, 1)
            
            p_end_dt = next_month - timedelta(days=1)
            
            p_start = current.strftime('%Y-%m-%d')
            p_end = p_end_dt.strftime('%Y-%m-%d')
            
            periods.append({
                'label': f"{p_start} ~ {p_end}",
                'start': p_start,
                'end': p_end
            })
            current = next_month
            
        return periods

    def get_history_summary(self, start_date_str, end_date_str):
        records = self.get_records_by_range(start_date_str, end_date_str)
        total_hours = sum(r.get('hours', 0) for r in records)
        total_amount = sum(r['amount'] for r in records)
        
        return {
            "records": records,
            "total_hours": total_hours,
            "total_amount": total_amount,
            "record_count": len(records)
        }

    def _to_dict(self, record):
        return {
            'id': record.id,
            'date': record.date,
            'type': record.type,
            'start_time': record.start_time,
            'end_time': record.end_time,
            'hours': record.hours,
            'rate': record.rate,
            'amount': record.amount,
            'note': record.note
        }
