from models import db, SalaryRecord, UserSettings, Company
from flask_login import current_user
from datetime import datetime, timedelta
from sqlalchemy import func

def _apply_holiday_pay(date_str: str, rate: float, hours: float, note: str | None) -> tuple[float, float, str | None]:
    """
    Check if date_str is a Taiwan national holiday.
    Returns (base_rate, amount, updated_note).
    - base_rate: always the original hourly rate (for display in UI)
    - amount:    hours × rate × 2 on holidays, hours × rate on normal days
    """
    try:
        from services.tw_holidays import is_holiday
        holiday_name = is_holiday(date_str)
    except Exception:
        holiday_name = None

    if holiday_name:
        amount = int(hours * rate * 2)   # 工資加倍，rate 保持原始值
        holiday_note = f"【國定假日：{holiday_name}】工資加倍（{hours:.1f}h × {rate:.0f} × 2 = ${amount}）"
        if note:
            updated_note = holiday_note + " " + note
        else:
            updated_note = holiday_note
    else:
        amount = int(hours * rate)
        updated_note = note

    return rate, amount, updated_note  # base_rate 不變

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
            note=record_data.get('note'),
            company_id=record_data.get('company_id') or None
        )
        
        if new_record.type == 'shift':
            start_t = record_data.get('start_time')
            end_t = record_data.get('end_time')
            new_record.start_time = start_t
            new_record.end_time = end_t
            
            if start_t and end_t:
                new_record.hours = self._calculate_hours(start_t, end_t)
            
            # Rate: use company rate if company_id given, else fall back to settings
            raw_rate = record_data.get('rate')
            settings = self.get_settings()
            default_rate = float(settings.get('hourly_rate', 183.0))
            # If company_id provided, load company's hourly_rate
            if new_record.company_id:
                company = Company.query.get(new_record.company_id)
                if company:
                    default_rate = company.hourly_rate
            
            base_rate = default_rate if not raw_rate else (float(raw_rate) if str(raw_rate).strip() else default_rate)

            # Holiday pay: double rate if national holiday
            effective_rate, amount, holiday_note = _apply_holiday_pay(
                new_record.date, base_rate, new_record.hours, record_data.get('note')
            )
            new_record.rate = effective_rate
            new_record.amount = amount
            new_record.note = holiday_note
            
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
        if 'company_id' in record_data: record.company_id = record_data['company_id'] or None
        
        if record.type == 'shift':
            if 'start_time' in record_data: record.start_time = record_data['start_time']
            if 'end_time' in record_data: record.end_time = record_data['end_time']
            
            if record.start_time and record.end_time:
                record.hours = self._calculate_hours(record.start_time, record.end_time)
                
            # Handle rate: if provided, use it. If empty or not provided, calculate default.
            raw_rate = record_data.get('rate')
            if raw_rate is not None and str(raw_rate).strip() != '':
                try:
                    base_rate = float(raw_rate)
                except ValueError:
                    base_rate = record.rate
            else:
                # Need to fallback to company rate or default settings rate
                settings = self.get_settings()
                default_rate = float(settings.get('hourly_rate', 183.0))
                if record.company_id:
                    company = Company.query.get(record.company_id)
                    if company:
                        default_rate = company.hourly_rate
                base_rate = default_rate

            # Strip old holiday note prefix before re-applying
            existing_note = record.note or ''
            if '【國定假日' in existing_note and '】' in existing_note:
                existing_note = existing_note.split('】', 1)[-1].strip()

            base_rate = record.rate
            new_rate, amount, updated_note = _apply_holiday_pay(
                record.date, base_rate, record.hours,
                record_data.get('note', existing_note)
            )
            record.rate = new_rate   # always base rate
            record.amount = amount
            record.note = updated_note
            
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

        import calendar

        # Find min and max record dates
        result = db.session.query(
            func.min(SalaryRecord.date),
            func.max(SalaryRecord.date)
        ).filter_by(user_id=current_user.id).first()

        if not result or not result[0]:
            now = datetime.now()
            min_date = now - timedelta(days=30)
            max_date = now + timedelta(days=30)
        else:
            min_date = datetime.strptime(result[0], '%Y-%m-%d')
            max_date = datetime.strptime(result[1], '%Y-%m-%d')

        def period_start_for(d):
            return d.replace(day=1)

        def next_period_start(p_start):
            if p_start.month == 12:
                return datetime(p_start.year + 1, 1, 1)
            else:
                return datetime(p_start.year, p_start.month + 1, 1)

        # Start one period before the earliest record
        current = period_start_for(min_date)
        now = datetime.now()
        final_limit = period_start_for(max_date) + timedelta(days=40)
        if final_limit < now:
            final_limit = now

        periods = []
        while current <= final_limit:
            last_day = calendar.monthrange(current.year, current.month)[1]
            p_start = f"{current.year:04d}-{current.month:02d}-01"
            p_end = f"{current.year:04d}-{current.month:02d}-{last_day:02d}"
            
            periods.append({
                'label': f"{current.year}年{current.month}月",
                'start': p_start,
                'end': p_end
            })
            current = next_period_start(current)

        # 反轉列表讓最新月份在最上面
        periods.reverse()
        return periods

    def get_history_summary(self, start_date_str, end_date_str, user=None):
        records = self.get_records_by_range(start_date_str, end_date_str, user=user)
        total_hours = sum(r.get('hours', 0) for r in records)
        total_amount = sum(r['amount'] for r in records)
        
        return {
            "records": records,
            "total_hours": total_hours,
            "total_amount": total_amount,
            "record_count": len(records)
        }

    def _to_dict(self, record):
        company_name = None
        company_color = None
        if record.company_id and record.company:
            company_name = record.company.name
            company_color = record.company.color
        return {
            'id': record.id,
            'date': record.date,
            'type': record.type,
            'start_time': record.start_time,
            'end_time': record.end_time,
            'hours': record.hours,
            'rate': record.rate,
            'amount': record.amount,
            'note': record.note,
            'company_id': record.company_id,
            'company_name': company_name,
            'company_color': company_color,
        }
