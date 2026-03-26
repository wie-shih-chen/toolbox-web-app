import datetime
from datetime import timedelta
from app import db
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
                "note": r.note
            }
            for r in records
        ]

    def add_record(self, start_date, end_date=None, note=None):
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

            # Also update the user's average cycle length dynamically
            self.settings.avg_period_cycle = self._calculate_avg_cycle([cycle_length])

        new_record = PeriodRecord(
            user_id=self.user_id,
            start_date=start_date,
            end_date=end_date,
            cycle_length=cycle_length,
            note=note
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

    def update_record(self, record_id, start_date, end_date=None, note=None):
        record = PeriodRecord.query.filter_by(id=record_id, user_id=self.user_id).first()
        if not record:
            return {"success": False, "error": "Record not found"}

        old_start_date = record.start_date
        record.start_date = start_date
        record.end_date = end_date
        record.note = note

        if old_start_date != start_date:
            # Recalculate cycle lengths for this and adjacent records
            self._recalculate_all_cycle_lengths()

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

        # Update average
        self.settings.avg_period_cycle = self._calculate_avg_cycle([r.cycle_length for r in records if r.cycle_length])

    def _calculate_avg_cycle(self, latest_cycles=None):
        """加權平均：最近的週期占更高比重"""
        records = PeriodRecord.query.filter(
            PeriodRecord.user_id == self.user_id,
            PeriodRecord.cycle_length.isnot(None)
        ).order_by(PeriodRecord.start_date.desc()).limit(6).all()
        
        cycles = [r.cycle_length for r in records]
        if latest_cycles:
            cycles = latest_cycles + cycles  # Prepend newest
        
        # Filter outliers (14~90 days)
        cycles = [c for c in cycles if 14 <= c <= 90]
        if not cycles:
            return self.settings.avg_period_cycle or 28
        
        # Weights: 6, 5, 4, 3, 2, 1 (newest first)
        weights = list(range(len(cycles), 0, -1))
        weighted_sum = sum(c * w for c, w in zip(cycles, weights))
        total_weight = sum(weights)
        return int(round(weighted_sum / total_weight))

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

    def update_settings(self, avg_period_cycle, avg_period_duration):
        self.settings.avg_period_cycle = int(avg_period_cycle)
        self.settings.avg_period_duration = int(avg_period_duration)
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
        """回傳今日生理期狀態（是否在經期、第幾天、距離下次幾天、是否有未結束紀錄）。"""
        today = datetime.datetime.now()
        today_str = today.strftime('%Y-%m-%d')

        all_records = PeriodRecord.query.filter_by(user_id=self.user_id).order_by(PeriodRecord.start_date.desc()).all()
        in_period = False
        period_day = None
        active_id = None
        has_open_record = False

        for r in all_records:
            start_dt = datetime.datetime.strptime(r.start_date, '%Y-%m-%d')
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
        preds = self.get_predictions(months=3)
        if preds:
            next_start = datetime.datetime.strptime(preds[0]['period_start'], '%Y-%m-%d')
            days_until_next = (next_start - today).days

        return {
            "is_in_period": in_period,
            "period_day": period_day,
            "days_until_next": days_until_next,
            "has_open_record": has_open_record,
            "active_record_id": active_id
        }


    def get_predictions(self, months=3):
        """
        Predict future periods based on the latest record and average cycle length.
        Returns a list of prediction objects for the next `months` periods.
        """
        avg_cycle = self.settings.avg_period_cycle or 28
        duration = self.settings.avg_period_duration or 5

        latest_record = PeriodRecord.query.filter_by(user_id=self.user_id).order_by(PeriodRecord.start_date.desc()).first()
        
        predictions = []
        if not latest_record:
            return predictions

        current_date = datetime.datetime.strptime(latest_record.start_date, '%Y-%m-%d')
        
        for i in range(months):
            # 1. 預測下次經期 = 上次第一天 + 平均週期
            predicted_start = current_date + timedelta(days=avg_cycle)
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
            
        # 2. Add past predictions (each history record predicting the next)
        if len(history) > 1:
            avg_cycle = self.settings.avg_period_cycle or 28
            duration = self.settings.avg_period_duration or 5
            for r in history[1:]:
                past_start_dt = datetime.datetime.strptime(r['start_date'], '%Y-%m-%d')
                p_start = past_start_dt + timedelta(days=avg_cycle)
                p_end = p_start + timedelta(days=duration - 1)
                o_day = p_start - timedelta(days=14)
                f_start = o_day - timedelta(days=5)
                f_end = o_day + timedelta(days=1)
                
                p = {
                    "period_start": p_start.strftime('%Y-%m-%d'),
                    "period_end": p_end.strftime('%Y-%m-%d'),
                    "ovulation_day": o_day.strftime('%Y-%m-%d'),
                    "fertile_window_start": f_start.strftime('%Y-%m-%d'),
                    "fertile_window_end": f_end.strftime('%Y-%m-%d')
                }
                events.extend(self._create_prediction_events(p, f"past_pred_{r['id']}"))

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
        
        # predicted period
        events.append({
            "id": f"{prefix_id}_period",
            "groupId": "predicted_period",
            "title": "預測經期",
            "start": p_start.strftime('%Y-%m-%d'),
            "end": p_end_exclusive.strftime('%Y-%m-%d'),
            "backgroundColor": "transparent",
            "borderColor": "#ffa39e", # Light red
            "textColor": "#cf1322",
            "className": "dashed-border",
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
