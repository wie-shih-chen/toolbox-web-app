from models import db, SalaryRecord, ExpenseRecord
from services.salary_service import SalaryService
from services.expense_service import ExpenseService
import openpyxl
import io
from flask import send_file

class DataService:
    @staticmethod
    def export_all_data(user_id):
        """
        Export all user data (Salary & Expense) to Excel.
        Returns: BytesIO object containing the .xlsx file
        """
        # Fetch Data
        salary_records = SalaryRecord.query.filter_by(user_id=user_id).all()
        expense_records = ExpenseRecord.query.filter_by(user_id=user_id).all()
        
        # Create Workbook
        wb = openpyxl.Workbook()
        
        # --- Salary Sheet ---
        ws_salary = wb.active
        ws_salary.title = "薪資紀錄"
        
        if salary_records:
            headers = ["Date", "Type", "Amount", "Start Time", "End Time", "Hours", "Rate", "Note"]
            ws_salary.append(headers)
            for r in salary_records:
                ws_salary.append([
                    r.date, r.type, r.amount, r.start_time, r.end_time, r.hours, r.rate, r.note
                ])
        else:
            ws_salary.append(["無資料"])
            
        # --- Expense Sheet ---
        ws_expense = wb.create_sheet(title="記帳紀錄")
        
        if expense_records:
            headers = ["Timestamp", "Category", "Amount", "Note"]
            ws_expense.append(headers)
            for r in expense_records:
                ws_expense.append([
                    r.timestamp, r.category, r.amount, r.note
                ])
        else:
            ws_expense.append(["無資料"])
                
        # Save to BytesIO
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        return output

    @staticmethod
    def reset_data(user_id, module):
        """
        Reset data for a specific module.
        module: 'salary', 'expense', or 'all'
        """
        try:
            if module == 'salary' or module == 'all':
                SalaryRecord.query.filter_by(user_id=user_id).delete()
                
            if module == 'expense' or module == 'all':
                ExpenseRecord.query.filter_by(user_id=user_id).delete()
                
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Reset Error: {e}")
            return False
