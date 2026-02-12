from models import db, SalaryRecord, ExpenseRecord
from services.salary_service import SalaryService
from services.expense_service import ExpenseService
import pandas as pd
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
        
        # Process Salary Data
        salary_data = []
        for r in salary_records:
            salary_data.append({
                "Date": r.date,
                "Type": r.type,
                "Amount": r.amount,
                "Start Time": r.start_time,
                "End Time": r.end_time,
                "Hours": r.hours,
                "Rate": r.rate,
                "Note": r.note
            })
            
        # Process Expense Data
        expense_data = []
        for r in expense_records:
            expense_data.append({
                "Timestamp": r.timestamp,
                "Category": r.category,
                "Amount": r.amount,
                "Note": r.note
            })
            
        # Create DataFrame
        df_salary = pd.DataFrame(salary_data)
        df_expense = pd.DataFrame(expense_data)
        
        # Write to Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            if not df_salary.empty:
                df_salary.to_excel(writer, sheet_name='薪資紀錄', index=False)
            else:
                pd.DataFrame(["無資料"]).to_excel(writer, sheet_name='薪資紀錄', index=False, header=False)
                
            if not df_expense.empty:
                df_expense.to_excel(writer, sheet_name='記帳紀錄', index=False)
            else:
                pd.DataFrame(["無資料"]).to_excel(writer, sheet_name='記帳紀錄', index=False, header=False)
                
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
