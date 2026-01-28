import json
import os
import uuid
from datetime import datetime, timedelta
from config import Config

class ExpenseService:
    def __init__(self):
        self.data_file = os.path.join(os.path.dirname(Config.SALARY_DATA_FILE), 'expense_data.json')
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        if not os.path.exists(self.data_file):
            self._save_data({"settings": {"monthly_budget": 10000}, "records": []})

    def _load_data(self):
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {"settings": {"monthly_budget": 10000}, "records": []}

    def _save_data(self, data):
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Error saving expense data: {e}")
            return False

    def get_all_records(self):
        data = self._load_data()
        return data.get('records', [])

    def add_record(self, record_data):
        data = self._load_data()
        new_record = record_data.copy()
        new_record['id'] = str(uuid.uuid4())
        
        # Ensure timestamp if not provided
        if 'timestamp' not in new_record:
            new_record['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Ensure price is numeric
        try:
            new_record['amount'] = float(new_record['amount'])
        except:
            new_record['amount'] = 0.0

        data['records'].append(new_record)
        self._save_data(data)
        return new_record

    def update_record(self, record_id, record_data):
        data = self._load_data()
        records = data.get('records', [])
        for i, r in enumerate(records):
            if r['id'] == record_id:
                r.update(record_data)
                try:
                    r['amount'] = float(r['amount'])
                except:
                    r['amount'] = 0.0
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

    def get_current_period(self):
        """
        Calculate current billing period: 10th to 10th.
        Example: If today is Jan 29, period is Jan 10 to Feb 10.
        If today is Feb 5, period is Jan 10 to Feb 10.
        If today is Feb 11, period is Feb 10 to Mar 10.
        """
        now = datetime.now()
        year = now.year
        month = now.month

        if now.day < 10:
            # Current period started last month 10th
            start_date = datetime(year, month - 1, 10) if month > 1 else datetime(year - 1, 12, 10)
            end_date = datetime(year, month, 10)
        else:
            # Current period started this month 10th
            start_date = datetime(year, month, 10)
            end_date = datetime(year, month + 1, 10) if month < 12 else datetime(year + 1, 1, 10)
            
        return start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')

    def get_summary(self, start_date_str, end_date_str):
        records = self.get_all_records()
        filtered = []
        total = 0
        categories = {}

        for r in records:
            # Record date is usually the first 10 chars of timestamp YYYY-MM-DD
            rec_date = r['timestamp'][:10]
            if start_date_str <= rec_date < end_date_str:
                filtered.append(r)
                total += r['amount']
                cat = r.get('category', '其他')
                categories[cat] = categories.get(cat, 0) + r['amount']

        # Sort records by timestamp descending
        filtered.sort(key=lambda x: x['timestamp'], reverse=True)

        return {
            "records": filtered,
            "total_amount": total,
            "category_split": categories,
            "period": {"start": start_date_str, "end": end_date_str}
        }
