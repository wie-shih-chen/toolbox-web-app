from models import db, SalaryRecord, UserSettings, Company
from flask_login import current_user
from datetime import datetime, timedelta
from sqlalchemy import func

def _calculate_pay_and_note(date_str: str, rate: float, hours: float, note: str | None, enable_overtime: bool = False) -> tuple[float, float, str | None]:
    """
    Calculate final pay amount considering national holidays or overtime.
    Returns (base_rate, amount, updated_note).
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
        if enable_overtime:
            amount, updated_note = _apply_overtime_pay(rate, hours, note)
        else:
            amount = int(hours * rate)
            updated_note = note

    return rate, amount, updated_note  # base_rate 不變

def _apply_overtime_pay(rate: float, hours: float, note: str | None) -> tuple[int, str | None]:
    if hours <= 8:
        return int(hours * rate), note
    
    amount = rate * 8
    calc_str = f"8h × {rate:.0f}"
    
    if hours <= 10:
        ot_hours = hours - 8
        amount += rate * 1.34 * ot_hours
        calc_str += f" + {ot_hours:.1f}h × {rate:.0f} × 1.34"
    else:
        ot_hours_2 = hours - 10
        amount += rate * 1.34 * 2
        amount += rate * 1.67 * ot_hours_2
        calc_str += f" + 2h × {rate:.0f} × 1.34 + {ot_hours_2:.1f}h × {rate:.0f} × 1.67"
        
    ot_note = f"【勞基法加班】（{calc_str} = ${int(amount)}）"
    new_note = f"{ot_note} {note}".strip() if note else ot_note
    if ot_note in (note or ""):
        new_note = note
    
    return int(amount), new_note
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

    @staticmethod
    def _evaluate_rule_conditions(rule, start_time_str, total_hours):
        conditions = rule.get('conditions', [])
        if not conditions:
            return False
            
        for cond in conditions:
            var = cond.get('var')
            op = cond.get('op')
            val = cond.get('val')
            
            try:
                if var == 'total_hours':
                    actual = float(total_hours)
                    target = float(val)
                elif var == 'start_time':
                    actual = datetime.strptime(start_time_str, '%H:%M').time()
                    target = datetime.strptime(str(val), '%H:%M').time()
                else:
                    return False
                    
                if op == '>':
                    if not (actual > target): return False
                elif op == '>=':
                    if not (actual >= target): return False
                elif op == '<':
                    if not (actual < target): return False
                elif op == '<=':
                    if not (actual <= target): return False
                elif op == '==':
                    if not (actual == target): return False
                elif op == '!=':
                    if not (actual != target): return False
                else:
                    return False
            except (ValueError, TypeError):
                return False
                
        return True

    def _calculate_hours(self, start_time_str, end_time_str, company_id=None):
        try:
            start_dt = datetime.strptime(start_time_str, '%H:%M')
            end_dt = datetime.strptime(end_time_str, '%H:%M')
            
            if end_dt < start_dt:
                end_dt += timedelta(days=1)
                
            delta = end_dt - start_dt
            total_hours = delta.total_seconds() / 3600.0
            
            # Apply break rules if company is specified
            deduct_hours = 0.0
            if company_id:
                company = Company.query.get(company_id)
                if company and company.break_rules:
                    try:
                        import json
                        rules = json.loads(company.break_rules)
                        
                        legacy_rules = [r for r in rules if r.get('type') != 'logic']
                        logic_rules = [r for r in rules if r.get('type') == 'logic']
                        
                        logic_matched = False
                        for rule in logic_rules:
                            if self._evaluate_rule_conditions(rule, start_time_str, total_hours):
                                deduct_hours = float(rule.get('deduct', 0))
                                logic_matched = True
                                break
                                
                        if not logic_matched:
                            # Sort legacy rules by threshold descending
                            legacy_rules.sort(key=lambda x: float(x.get('threshold', 0)), reverse=True)
                            for rule in legacy_rules:
                                threshold = float(rule.get('threshold', 0))
                                deduct = float(rule.get('deduct', 0))
                                if total_hours >= threshold:
                                    deduct_hours = deduct
                                    break
                    except Exception as e:
                        pass
            
            return max(0.0, total_hours - deduct_hours), deduct_hours
        except (ValueError, TypeError):
            return 0.0, 0.0

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
                new_record.hours, deduct = self._calculate_hours(start_t, end_t, new_record.company_id)
                if deduct > 0:
                    current_note = record_data.get('note') or ''
                    record_data['note'] = f"(已扣除休息 {deduct}h) {current_note}".strip()
            
            # Rate: use company rate if company_id given, else fall back to settings
            raw_rate = record_data.get('rate')
            settings = self.get_settings()
            default_rate = float(settings.get('hourly_rate', 183.0))
            enable_ot = False
            
            # If company_id provided, load company's hourly_rate and overtime config
            if new_record.company_id:
                company = Company.query.get(new_record.company_id)
                if company:
                    default_rate = company.hourly_rate
                    enable_ot = company.enable_overtime
            
            base_rate = default_rate if not raw_rate else (float(raw_rate) if str(raw_rate).strip() else default_rate)

            # Calculate amount (handles holidays and always applies overtime)
            effective_rate, amount, final_note = _calculate_pay_and_note(
                new_record.date, base_rate, new_record.hours, record_data.get('note'), True
            )
            new_record.rate = effective_rate
            new_record.amount = amount
            new_record.note = final_note
            
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
            
            deduct = 0.0
            if record.start_time and record.end_time:
                record.hours, deduct = self._calculate_hours(record.start_time, record.end_time, record.company_id)
                
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
            incoming_note = record_data.get('note')
            if incoming_note is None:
                incoming_note = record.note or ''
                
            if '【國定假日' in incoming_note and '】' in incoming_note:
                incoming_note = incoming_note.split('】', 1)[-1].strip()
                if incoming_note.startswith('工資加倍（'):
                    incoming_note = incoming_note.split('）', 1)[-1].strip()

            # Remove old overtime note if present
            if '【勞基法加班】' in incoming_note:
                incoming_note = incoming_note.split('）', 1)[-1].strip()
            incoming_note = incoming_note.replace("(含勞基法加班費)", "").strip()
            
            # Remove old break note if present
            if '(已扣除休息' in incoming_note or '☕ 扣休' in incoming_note:
                import re
                incoming_note = re.sub(r'\(已扣除休息 \d+(\.\d+)?h\)\s*', '', incoming_note)
                incoming_note = re.sub(r'☕ 扣休\d+(\.\d+)?h\s*', '', incoming_note).strip()

            if deduct > 0:
                incoming_note = f"(已扣除休息 {deduct}h) {incoming_note}".strip()

            base_rate = record.rate

            new_rate, amount, updated_note = _calculate_pay_and_note(
                record.date, base_rate, record.hours,
                incoming_note, True
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

    def recalculate_company_records(self, company_id=None):
        if not current_user.is_authenticated:
            return
        
        query = SalaryRecord.query.filter_by(user_id=current_user.id, type='shift')
        if company_id is not None:
            query = query.filter_by(company_id=company_id)
            
        records = query.all()
        for r in records:
            # Re-trigger calculation by sending empty dict to update_record
            # update_record will use existing start/end and recalculate hours/amount
            self.update_record(r.id, {})
            
        db.session.commit()
