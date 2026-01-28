import json
import os
import uuid
from datetime import datetime, timedelta
from config import Config

class SalaryService:
    def __init__(self):
        self.data_file = Config.SALARY_DATA_FILE
        self._ensure_data_integrity()

    def _load_data(self):
        if not os.path.exists(self.data_file):
             return {"settings": {"hourly_rate": 183}, "records": [], "rate_history": []}
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
             return {"settings": {"hourly_rate": 183}, "records": [], "rate_history": []}

    def _save_data(self, data):
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Error saving data: {e}")
            return False

    def _ensure_data_integrity(self):
        data = self._load_data()
        updated = False
        if 'rate_history' not in data:
            data['rate_history'] = []
            if 'settings' in data and 'hourly_rate' in data['settings']:
                data['rate_history'].append({
                    'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'rate': data['settings']['hourly_rate']
                })
            updated = True
        
        if updated:
            self._save_data(data)

    def get_all_records(self):
        data = self._load_data()
        return data.get('records', [])

    def get_records_by_range(self, start_date_str, end_date_str):
        """
        Get records within a date range (inclusive).
        Dates should be 'YYYY-MM-DD' strings.
        """
        data = self._load_data()
        records = data.get('records', [])
        
        filtered = []
        for r in records:
            if start_date_str <= r['date'] <= end_date_str:
                filtered.append(r)
        
        # Sort by date and time
        filtered.sort(key=lambda x: (x['date'], x.get('start_time', '')))
        return filtered

    def _calculate_hours(self, start_time_str, end_time_str):
        """
        Calculate duration in hours between two time strings in 'HH:MM' format.
        Handles cases where end time is after midnight (not implemented yet, but good for future).
        """
        try:
            start_dt = datetime.strptime(start_time_str, '%H:%M')
            end_dt = datetime.strptime(end_time_str, '%H:%M')
            
            # If end time is before start time, assume it's the next day
            if end_dt < start_dt:
                end_dt += timedelta(days=1)
                
            delta = end_dt - start_dt
            return delta.total_seconds() / 3600.0
        except (ValueError, TypeError):
            return 0.0

    def add_record(self, record_data):
        data = self._load_data()
        
        new_record = record_data.copy()
        new_record['id'] = str(uuid.uuid4())
        
        # Calculate amount if shift
        if new_record['type'] == 'shift':
            # Calculate hours from times if not provided or empty
            start_t = new_record.get('start_time')
            end_t = new_record.get('end_time')
            
            if start_t and end_t:
                new_record['hours'] = self._calculate_hours(start_t, end_t)
            
            # Ensure proper types
            try:
                hours = float(new_record.get('hours', 0))
            except (ValueError, TypeError):
                hours = 0.0
            
            # Handle rate: empty string or missing -> use default
            raw_rate = new_record.get('rate')
            if raw_rate == '' or raw_rate is None:
                rate = float(data['settings']['hourly_rate'])
            else:
                try:
                    rate = float(raw_rate)
                except (ValueError, TypeError):
                    rate = float(data['settings']['hourly_rate'])
                
            new_record['hours'] = hours
            new_record['rate'] = rate
            new_record['amount'] = hours * rate
        else:
            # Bonus
            try:
                new_record['amount'] = int(new_record['amount'])
            except (ValueError, TypeError):
                new_record['amount'] = 0

        data['records'].append(new_record)
        self._save_data(data)
        return new_record

    def update_record(self, record_id, record_data):
        data = self._load_data()
        records = data.get('records', [])
        
        for i, r in enumerate(records):
            if r['id'] == record_id:
                # Update fields
                r.update(record_data)
                
                # Recalculate if shift
                if r['type'] == 'shift':
                    start_t = r.get('start_time')
                    end_t = r.get('end_time')
                    if start_t and end_t:
                        r['hours'] = self._calculate_hours(start_t, end_t)
                    
                    try:
                        r['hours'] = float(r.get('hours', 0))
                    except (ValueError, TypeError):
                        r['hours'] = 0.0
                    
                    # Handle rate: empty string or missing -> use default
                    raw_rate = r.get('rate')
                    if raw_rate == '' or raw_rate is None:
                        rate = float(data['settings']['hourly_rate'])
                    else:
                        try:
                            rate = float(raw_rate)
                        except (ValueError, TypeError):
                            rate = float(data['settings']['hourly_rate'])
                        
                    r['rate'] = rate
                    r['amount'] = r['hours'] * r['rate']
                else:
                    try:
                        r['amount'] = int(r['amount'])
                    except (ValueError, TypeError):
                        r['amount'] = 0
                
                records[i] = r
                self._save_data(data)
                return r
        return None

    def delete_record(self, record_id):
        data = self._load_data()
        original_len = len(data['records'])
        data['records'] = [r for r in data['records'] if r['id'] != record_id]
        
        if len(data['records']) < original_len:
            self._save_data(data)
            return True
        return False

    def get_settings(self):
        data = self._load_data()
        return data.get('settings', {})

    def update_settings(self, settings_data):
        data = self._load_data()
        
        if 'hourly_rate' in settings_data:
            new_rate = float(settings_data['hourly_rate'])
            old_rate = data['settings'].get('hourly_rate')
            
            if new_rate != old_rate:
                data['settings']['hourly_rate'] = new_rate
                # Record history
                if 'rate_history' not in data:
                    data['rate_history'] = []
                data['rate_history'].append({
                    'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'rate': new_rate
                })
        
        self._save_data(data)
        return data['settings']

    def calculate_weekly_summary(self, start_date_str):
        """
        Calculate totals for a week starting from start_date_str
        """
        start = datetime.strptime(start_date_str, '%Y-%m-%d')
        end = start + timedelta(days=6)
        end_str = end.strftime('%Y-%m-%d')
        
        records = self.get_records_by_range(start_date_str, end_str)
        
        total_hours = 0
        total_amount = 0
        
        for r in records:
            total_hours += float(r.get('hours', 0))
            total_amount += r['amount']
            
        return {
            "total_hours": total_hours,
            "total_amount": int(total_amount),
            "record_count": len(records)
        }

    def copy_week_records(self, target_week_start_str):
        """
        Copy records from the previous week to the target week.
        target_week_start_str: The Monday of the week to paste INTO.
        """
        target_start = datetime.strptime(target_week_start_str, '%Y-%m-%d')
        source_start = target_start - timedelta(days=7)
        source_end = source_start + timedelta(days=6)
        
        source_start_str = source_start.strftime('%Y-%m-%d')
        source_end_str = source_end.strftime('%Y-%m-%d')
        
        source_records = self.get_records_by_range(source_start_str, source_end_str)
        if not source_records:
            return 0
            
        data = self._load_data()
        current_rate = data['settings']['hourly_rate']
        count = 0
        
        for r in source_records:
            # Calculate new date
            old_date = datetime.strptime(r['date'], '%Y-%m-%d')
            day_diff = (old_date - source_start).days
            new_date = target_start + timedelta(days=day_diff)
            
            new_record = r.copy()
            new_record['id'] = str(uuid.uuid4())
            new_record['date'] = new_date.strftime('%Y-%m-%d')
            
            if new_record['type'] == 'shift':
                new_record['rate'] = current_rate
                new_record['amount'] = new_record['hours'] * current_rate
            
            data['records'].append(new_record)
            count += 1
            
        self._save_data(data)
        return count

    def clear_week_records(self, week_start_str):
        """
        Delete all records in the specified week.
        """
        start = datetime.strptime(week_start_str, '%Y-%m-%d')
        end = start + timedelta(days=6)
        start_str = start.strftime('%Y-%m-%d')
        end_str = end.strftime('%Y-%m-%d')
        
        data = self._load_data()
        original_records = data.get('records', [])
        
        # Keep records that are NOT in the range
        new_records = []
        deleted_count = 0
        
        for r in original_records:
            if start_str <= r['date'] <= end_str:
                deleted_count += 1
            else:
                new_records.append(r)
                
        if deleted_count > 0:
            data['records'] = new_records
            self._save_data(data)
            
        return deleted_count

    def generate_csv_export(self):
        """
        Generate CSV content string
        """
        records = self.get_all_records()
        # Sort by date
        records.sort(key=lambda x: x['date'])
        
        lines = ["日期,類型,開始時間,結束時間,時數,時薪/金額,備註"]
        
        total_hours = 0
        total_amount = 0
        
        for r in records:
            if r['type'] == 'shift':
                line = f"{r['date']},排班,{r['start_time']},{r['end_time']},{r['hours']},{r['rate']},"
                total_hours += r['hours']
                total_amount += r['amount']
            else:
                # 獎金: 跳過 開始、結束 欄位 (2個逗號)，時數在第5欄，金額在第6欄
                line = f"{r['date']},獎金,,,{r.get('hours', '')},{r['amount']},{r.get('note', '')}"
                total_amount += r['amount']
            lines.append(line)
        
        # Add summary line: 總計,,,,時數,金額,
        lines.append(f"總計,,,,{total_hours},{total_amount},")
            
        return "\n".join(lines)

    def get_monthly_periods(self):
        """
        Generate a list of available periods based on existing data range.
        Period: 10th of Month X to 10th of Month X+1 (inclusive).
        We will look at min_date and max_date in records to determine range.
        If no records, return default range around today.
        """
        records = self.get_all_records()
        if not records:
            now = datetime.now()
            start_date = now - timedelta(days=30)
            end_date = now + timedelta(days=30)
        else:
            dates = [r['date'] for r in records]
            dates.sort()
            start_date = datetime.strptime(dates[0], '%Y-%m-%d')
            end_date = datetime.strptime(dates[-1], '%Y-%m-%d')
            
            # Extend a bit to be safe/useful
            start_date -= timedelta(days=30)
            end_date += timedelta(days=30)
            
        # Normalize to 10th
        # If start_date day < 10, then period starts prev month 10th
        if start_date.day < 10:
            current = datetime(start_date.year, start_date.month, 10) - timedelta(days=32) # Go back to prev month
            current = datetime(current.year, current.month, 10)
        else:
            current = datetime(start_date.year, start_date.month, 10)
            
        periods = []
        # Ensure we cover at least until today
        now = datetime.now()
        final_date = end_date if end_date > now else now
        
        # We want to ensure 'current' covers 'final_date'
        # i.e. loop until the START of the period is > final_date? 
        # No, until the END of the period covers final_date.
        
        while current <= final_date:
            next_period = current + timedelta(days=32)
            next_period = datetime(next_period.year, next_period.month, 10)
            
            period_str = f"{current.strftime('%Y-%m-%d')} ~ {next_period.strftime('%Y-%m-%d')}"
            periods.append({
                'label': period_str,
                'start': current.strftime('%Y-%m-%d'),
                'end': next_period.strftime('%Y-%m-%d')
            })
            current = next_period
            
        # Return Ascending (Oldest First) as requested "Order"
        return periods

    def get_history_summary(self, start_date_str, end_date_str):
        """
        Calculate summary for a custom period
        """
        records = self.get_records_by_range(start_date_str, end_date_str)
        
        total_hours = 0
        total_amount = 0
        
        for r in records:
            total_hours += float(r.get('hours', 0))
            total_amount += r['amount']
            
        return {
            "records": records,
            "total_hours": total_hours,
            "total_amount": int(total_amount),
            "record_count": len(records)
        }
