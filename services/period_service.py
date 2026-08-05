import datetime
from datetime import timedelta
import math
import statistics
from models import db
from models import PeriodRecord, UserSettings

class PeriodService:
    def __init__(self, user_id):
        self.user_id = user_id
        # Ensure user settings exist
        self.settings = UserSettings.query.filter_by(user_id=self.user_id).first()
        if not self.settings:
            self.settings = UserSettings(user_id=self.user_id)
            db.session.add(self.settings)
            db.session.commit()

    def get_history(self):
        records = PeriodRecord.query.filter_by(user_id=self.user_id).order_by(PeriodRecord.start_date.desc()).all()
        return [
            {
                "id": r.id,
                "start_date": r.start_date,
                "end_date": r.end_date,
                "cycle_length": r.cycle_length,
                "note": r.note,
                "exclude_from_avg": r.exclude_from_avg,
                "is_gap": (r.cycle_length or 0) > 60
            }
            for r in records
        ]

    def add_record(self, start_date, end_date=None, note=None, exclude_from_avg=False):
        # Check if there's an ongoing period record
        latest_record = PeriodRecord.query.filter_by(user_id=self.user_id).order_by(PeriodRecord.start_date.desc()).first()
        if latest_record and not latest_record.end_date:
            return {"success": False, "error": "上一次生理期尚未結束，無法新增！請先設定結束日期。"}

        # Calculate cycle length if there's a previous record
        prev_record = PeriodRecord.query.filter(
            PeriodRecord.user_id == self.user_id,
            PeriodRecord.start_date < start_date
        ).order_by(PeriodRecord.start_date.desc()).first()

        cycle_length = None
        if prev_record:
            sd = datetime.datetime.strptime(start_date, '%Y-%m-%d')
            prev_sd = datetime.datetime.strptime(prev_record.start_date, '%Y-%m-%d')
            cycle_length = (sd - prev_sd).days
            
            # Auto-exclude if > 60 days gap
            if cycle_length > 60:
                exclude_from_avg = True

        new_record = PeriodRecord(
            user_id=self.user_id,
            start_date=start_date,
            end_date=end_date,
            cycle_length=cycle_length,
            note=note,
            exclude_from_avg=exclude_from_avg
        )
        db.session.add(new_record)
        
        # If there's a next record, its cycle length needs recalculation
        next_record = PeriodRecord.query.filter(
            PeriodRecord.user_id == self.user_id,
            PeriodRecord.start_date > start_date
        ).order_by(PeriodRecord.start_date.asc()).first()
        
        if next_record:
            nsd = datetime.datetime.strptime(next_record.start_date, '%Y-%m-%d')
            sd = datetime.datetime.strptime(start_date, '%Y-%m-%d')
            next_record.cycle_length = (nsd - sd).days
            self.settings.avg_period_cycle = self._calculate_avg_cycle([])

        db.session.commit()
        return {"success": True, "id": new_record.id}

    def update_record(self, record_id, start_date, end_date=None, note=None, exclude_from_avg=None):
        record = PeriodRecord.query.filter_by(id=record_id, user_id=self.user_id).first()
        if not record:
            return {"success": False, "error": "Record not found"}

        old_start_date = record.start_date
        record.start_date = start_date
        record.end_date = end_date
        record.note = note
        
        if exclude_from_avg is not None:
            record.exclude_from_avg = exclude_from_avg

        if old_start_date != start_date:
            # Recalculate cycle lengths for this and adjacent records
            self._recalculate_all_cycle_lengths()
        else:
            # Just update average if exclusion status changed
            self.settings.avg_period_cycle = self._calculate_avg_cycle()

        db.session.commit()
        return {"success": True}

    def delete_record(self, record_id):
        record = PeriodRecord.query.filter_by(id=record_id, user_id=self.user_id).first()
        if not record:
            return {"success": False, "error": "Record not found"}

        db.session.delete(record)
        self._recalculate_all_cycle_lengths()
        db.session.commit()
        return {"success": True}

    def _recalculate_all_cycle_lengths(self):
        records = PeriodRecord.query.filter_by(user_id=self.user_id).order_by(PeriodRecord.start_date.asc()).all()
        for i in range(len(records)):
            if i == 0:
                records[i].cycle_length = None
            else:
                curr_sd = datetime.datetime.strptime(records[i].start_date, '%Y-%m-%d')
                prev_sd = datetime.datetime.strptime(records[i-1].start_date, '%Y-%m-%d')
                records[i].cycle_length = (curr_sd - prev_sd).days
                
                # Auto-exclude extremely long cycles if they haven't been manually set
                if records[i].cycle_length > 60 and records[i].exclude_from_avg is False:
                    records[i].exclude_from_avg = True

        # Update average
        self.settings.avg_period_cycle = self._calculate_avg_cycle([r.cycle_length for r in records if r.cycle_length and not r.exclude_from_avg])

    def _calculate_avg_cycle(self, latest_cycles=None):
        """加權平均：最近的週期占更高比重 (EMA 概念)"""
        records = PeriodRecord.query.filter(
            PeriodRecord.user_id == self.user_id,
            PeriodRecord.cycle_length.isnot(None),
            PeriodRecord.exclude_from_avg == False
        ).order_by(PeriodRecord.start_date.desc()).limit(6).all()
        
        cycles = [r.cycle_length for r in records]
        if latest_cycles:
            latest_cycles = [c for c in latest_cycles if c is not None]
            cycles = latest_cycles + cycles
        
        cycles = [c for c in cycles if 14 <= c <= 60]
        if not cycles:
            return self.settings.avg_period_cycle or 28
            
        if len(cycles) < 2:
            return int(round(sum(cycles) / len(cycles)))
            
        # 使用加權平均 (最新週期權重最高)
        weights = list(range(len(cycles), 0, -1))
        weighted_sum = sum(c * w for c, w in zip(cycles, weights))
        return int(round(weighted_sum / sum(weights)))

    def _calculate_avg_duration(self):
        """From actual records with both start and end date, calculate average period duration."""
        records = PeriodRecord.query.filter(
            PeriodRecord.user_id == self.user_id,
            PeriodRecord.end_date.isnot(None),
            PeriodRecord.end_date != ''
        ).order_by(PeriodRecord.start_date.desc()).limit(6).all()
        
        durations = []
        for r in records:
            try:
                s = datetime.datetime.strptime(r.start_date, '%Y-%m-%d')
                e = datetime.datetime.strptime(r.end_date, '%Y-%m-%d')
                d = (e - s).days + 1  # inclusive
                if 1 <= d <= 14:  # Sanity check
                    durations.append(d)
            except:
                continue
        
        if durations:
            # Weighted average (recent records have more weight)
            weights = list(range(len(durations), 0, -1))
            weighted_sum = sum(d * w for d, w in zip(durations, weights))
            return int(round(weighted_sum / sum(weights)))
        
        return self.settings.avg_period_duration or 5

    def update_settings(self, avg_period_cycle=None, avg_period_duration=None, 
                        period_notify_enabled=None, period_notify_time=None, 
                        period_notify_days_before=None, period_notify_period=None, 
                        period_notify_ovulation=None, stress_level=None, 
                        sleep_quality=None, anxiety_multiplier=None):
        if avg_period_cycle is not None:
            try:
                self.settings.avg_period_cycle = int(avg_period_cycle)
            except ValueError:
                pass
        if avg_period_duration is not None:
            try:
                self.settings.avg_period_duration = int(avg_period_duration)
            except ValueError:
                pass
        if period_notify_enabled is not None:
            self.settings.period_notify_enabled = bool(period_notify_enabled)
        if period_notify_time is not None:
            self.settings.period_notify_time = period_notify_time
        if period_notify_days_before is not None:
            self.settings.period_notify_days_before = int(period_notify_days_before)
        if period_notify_period is not None:
            self.settings.period_notify_period = bool(period_notify_period)
        if period_notify_ovulation is not None:
            self.settings.period_notify_ovulation = bool(period_notify_ovulation)
            
        db.session.commit()
        return {"success": True}

    def quick_start_today(self):
        """一鍵：今天開始新的經期。"""
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        existing = PeriodRecord.query.filter_by(user_id=self.user_id, start_date=today).first()
        if existing:
            return {"success": False, "error": "今日已有紀錄"}
        return self.add_record(today)

    def quick_end_today(self):
        """一鍵：把最近一筆未結束的紀錄結束日設為今天。"""
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        today_dt = datetime.datetime.strptime(today, '%Y-%m-%d')
        record = PeriodRecord.query.filter(
            PeriodRecord.user_id == self.user_id,
            PeriodRecord.end_date.is_(None) | (PeriodRecord.end_date == '')
        ).order_by(PeriodRecord.start_date.desc()).first()
        if not record:
            return {"success": False, "error": "沒有進行中的紀錄"}
        start_dt = datetime.datetime.strptime(record.start_date, '%Y-%m-%d')
        if today_dt < start_dt:
            return {"success": False, "error": "結束日期不能早於開始日期"}
        record.end_date = today
        db.session.commit()
        # Recalculate avg duration from actual records
        self.settings.avg_period_duration = self._calculate_avg_duration()
        db.session.commit()
        return {"success": True, "start_date": record.start_date, "end_date": today}

    def get_status(self):
        """回傳今日生理期狀態（機率模型版）。"""
        today = datetime.datetime.now()
        today_str = today.strftime('%Y-%m-%d')

        all_records = PeriodRecord.query.filter_by(user_id=self.user_id).order_by(PeriodRecord.start_date.desc()).all()
        in_period = False
        period_day = None
        active_id = None
        has_open_record = False
        latest_start_date = None

        for r in all_records:
            start_dt = datetime.datetime.strptime(r.start_date, '%Y-%m-%d')
            if latest_start_date is None:
                latest_start_date = start_dt
                
            if not r.end_date:  # None or empty string
                if start_dt <= today:
                    in_period = True
                    has_open_record = True
                    period_day = (today - start_dt).days + 1
                    active_id = r.id
                    break
            else:
                end_dt = datetime.datetime.strptime(r.end_date, '%Y-%m-%d')
                if start_dt <= today <= end_dt:
                    in_period = True
                    period_day = (today - start_dt).days + 1
                    active_id = r.id
                    break

        days_until_next = None
        probability = 0.0
        
        if not in_period and latest_start_date:
            days_since_last = (today - latest_start_date).days
            # Get standard deviation
            records_for_std = PeriodRecord.query.filter(
                PeriodRecord.user_id == self.user_id,
                PeriodRecord.cycle_length.isnot(None),
                PeriodRecord.exclude_from_avg == False
            ).order_by(PeriodRecord.start_date.desc()).limit(12).all()
            cycles = [r.cycle_length for r in records_for_std if 14 <= r.cycle_length <= 60]
            
            std_dev = statistics.pstdev(cycles) if len(cycles) > 1 else 3.0
            std_dev = max(1.0, std_dev) # Prevent division by zero
            
            # Dynamic mean (shifted by environment)
            shifted_mean = self._get_shifted_mean_cycle()

            # 3. 計算預計剩餘天數
            days_until_next = shifted_mean - days_since_last
            
            # 4. 直覺化機率計算 (Scaled PDF)
            import math
            if days_since_last <= shifted_mean:
                # Scaled Normal PDF: peak at 1.0 when days_since_last == shifted_mean
                probability = math.exp(-0.5 * ((days_since_last - shifted_mean) / std_dev) ** 2)
            else:
                probability = 0.99

        return {
            "is_in_period": in_period,
            "period_day": period_day,
            "days_until_next": days_until_next,
            "has_open_record": has_open_record,
            "active_record_id": active_id,
            "today_probability": round(probability * 100, 1)
        }

    def _get_shifted_mean_cycle(self):
        """根據環境變數 (壓力、焦慮) 平移平均週期"""
        mean_cycle = self.settings.avg_period_cycle or 28
        
        shift = 0
        if getattr(self.settings, 'anxiety_multiplier', 0) > 0.8:
            shift += 4
        elif getattr(self.settings, 'anxiety_multiplier', 0) > 0.5:
            shift += 2
            
        if getattr(self.settings, 'stress_level', 0) > 0.8:
            shift += 3
        elif getattr(self.settings, 'stress_level', 0) > 0.5:
            shift += 1
            
        return mean_cycle + shift


    def get_predictions(self, months=3):
        """
        Predict future periods based on the latest record and dynamic probability model.
        Returns a list of prediction objects for the next `months` periods.
        """
        shifted_avg_cycle = self._get_shifted_mean_cycle()
        duration = self.settings.avg_period_duration or 5

        latest_record = PeriodRecord.query.filter_by(user_id=self.user_id).order_by(PeriodRecord.start_date.desc()).first()
        
        predictions = []
        if not latest_record:
            return predictions

        current_date = datetime.datetime.strptime(latest_record.start_date, '%Y-%m-%d')
        
        for i in range(months):
            # 1. 預測下次經期 = 上次第一天 + 動態平均週期
            predicted_start = current_date + timedelta(days=shifted_avg_cycle)
            predicted_end = predicted_start + timedelta(days=duration - 1)
            
            # 2. 排卵日 = 預測下次經期 - 14 天
            ovulation_day = predicted_start - timedelta(days=14)
            
            # 3. 易孕期 = 排卵日前 5 天 ~ 後 1 天
            fertile_start = ovulation_day - timedelta(days=5)
            fertile_end = ovulation_day + timedelta(days=1)
            
            predictions.append({
                "period_start": predicted_start.strftime('%Y-%m-%d'),
                "period_end": predicted_end.strftime('%Y-%m-%d'),
                "ovulation_day": ovulation_day.strftime('%Y-%m-%d'),
                "fertile_window_start": fertile_start.strftime('%Y-%m-%d'),
                "fertile_window_end": fertile_end.strftime('%Y-%m-%d')
            })
            
            # Update current_date for the next iteration
            current_date = predicted_start
            
        return predictions

    def get_calendar_events(self, year, month):
        """
        Merge history records and predictions to create FullCalendar-compatible events.
        """
        events = []
        
        # 1. Add historical records
        # Filter loosely by year/month or just return all recent for simplicity
        history = self.get_history()
        for r in history:
            start_dt = datetime.datetime.strptime(r['start_date'], '%Y-%m-%d')
            # If end_date missing, only show the start date (1 day)
            end_dt = datetime.datetime.strptime(r['end_date'], '%Y-%m-%d') if r['end_date'] else start_dt
            
            # Fullcalendar end date is exclusive, so add 1 day
            cal_end_dt = end_dt + timedelta(days=1)
            
            events.append({
                "id": f"history_{r['id']}",
                "groupId": "period",
                "title": "經期",
                "start": start_dt.strftime('%Y-%m-%d'),
                "end": cal_end_dt.strftime('%Y-%m-%d'),
                "backgroundColor": "#ff4d4f", # Red
                "borderColor": "#ff4d4f",
                "textColor": "white",
                "extendedProps": {
                    "type": "history",
                    "note": r['note'],
                    "cycle_length": r['cycle_length']
                }
            })
            
        # 3. Add future predictions
        preds = self.get_predictions(months=6) # Get half year of predictions
        for i, p in enumerate(preds):
            events.extend(self._create_prediction_events(p, f"future_pred_{i}"))
            
        return events

    def _create_prediction_events(self, p, prefix_id):
        events = []
        p_start = datetime.datetime.strptime(p['period_start'], '%Y-%m-%d')
        p_end = datetime.datetime.strptime(p['period_end'], '%Y-%m-%d')
        p_end_exclusive = p_end + timedelta(days=1)
        
        # 預測經期 (單一區塊 + 漸層機率暈染)
        events.append({
            "id": f"{prefix_id}_period",
            "groupId": "predicted_period",
            "title": "預測經期",
            "start": p_start.strftime('%Y-%m-%d'),
            "end": p_end_exclusive.strftime('%Y-%m-%d'),
            "backgroundColor": "transparent",
            "borderColor": "transparent",
            "textColor": "#ffffff",
            "className": "predicted-period-gradient",
            "extendedProps": {"type": "predicted_period"}
        })
        
        # fertile window
        f_start = datetime.datetime.strptime(p['fertile_window_start'], '%Y-%m-%d')
        f_end = datetime.datetime.strptime(p['fertile_window_end'], '%Y-%m-%d')
        f_end_exclusive = f_end + timedelta(days=1)
        
        events.append({
            "id": f"{prefix_id}_fertile",
            "groupId": "fertile_window",
            "title": "易孕期",
            "start": f_start.strftime('%Y-%m-%d'),
            "end": f_end_exclusive.strftime('%Y-%m-%d'),
            "backgroundColor": "rgba(115, 209, 61, 0.2)", # Light green transparent
            "borderColor": "#73d13d",
            "textColor": "#b7eb8f",
            "extendedProps": {"type": "fertile_window"}
        })
        
        # ovulation day
        o_day = datetime.datetime.strptime(p['ovulation_day'], '%Y-%m-%d')
        events.append({
            "id": f"{prefix_id}_ovulation",
            "groupId": "ovulation",
            "title": "🥚 排卵日",
            "start": o_day.strftime('%Y-%m-%d'),
            "allDay": True,
            "backgroundColor": "rgba(255, 255, 255, 0.1)",
            "borderColor": "transparent",
            "textColor": "#73d13d",
            "extendedProps": {"type": "ovulation"}
        })
        
        return events
