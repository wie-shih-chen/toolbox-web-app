from models import db, UserSettings
from flask_login import current_user

class FinanceService:
    @staticmethod
    def calculate_taiwan_insurance(insurance_salary, dependents=0, pension_rate=0.0):
        """
        Calculates Taiwan Labor Insurance, Health Insurance, and Labor Pension deductions.
        Rates are based on 2024/2025 standards.
        """
        if insurance_salary <= 0:
            return {
                "labor_insurance": 0,
                "health_insurance": 0,
                "labor_pension": 0,
                "total_deductions": 0
            }

        # 1. Labor Insurance (勞保)
        # 2024 Rate: 11% (Ordinary) + 1% (Employment Insurance) = 12%
        # Employee pays 20%
        labor_rate = 0.12
        labor_insurance = round(insurance_salary * labor_rate * 0.20)

        # 2. Health Insurance (健保)
        # 2024 Rate: 5.17%
        # Employee pays 30%
        # Dependents: capped at 3 for calculation (max 1+3 = 4 people)
        health_rate = 0.0517
        effective_dependents = min(dependents, 3)
        health_insurance = round(insurance_salary * health_rate * 0.30 * (1 + effective_dependents))

        # 3. Labor Pension (勞退自提)
        # User defined (0% to 6%)
        labor_pension = round(insurance_salary * pension_rate)

        total_deductions = labor_insurance + health_insurance + labor_pension

        return {
            "labor_insurance": labor_insurance,
            "health_insurance": health_insurance,
            "labor_pension": labor_pension,
            "total_deductions": total_deductions
        }

    @staticmethod
    def estimate_income_tax(monthly_income):
        """
        Very simplified income tax estimation for Taiwan.
        Standard deduction and basic bracket (5%) for most users.
        """
        # Monthly threshold for withholding is approx 88k+ or based on table.
        # Here we just provide a very basic 5% estimation if above a certain threshold.
        annual_threshold = 423000 # Rough estimate for 2024 standard + personal deduction
        monthly_threshold = annual_threshold / 12

        if monthly_income <= monthly_threshold:
            return 0
        
        # Simple 5% on amount above threshold
        taxable = monthly_income - monthly_threshold
        return round(taxable * 0.05)

    def get_user_finance_summary(self, gross_salary, days=30, user=None):
        target_user = user or current_user
        if not target_user or not hasattr(target_user, 'settings'):
            return None
        
        settings = target_user.settings
        if not settings or not settings.enable_finance_tracking:
            return None
        
        # Calculate full monthly insurance
        monthly_insurance = self.calculate_taiwan_insurance(
            settings.insurance_salary,
            settings.health_insurance_dependents,
            settings.labor_pension_rate
        )
        
        # Pro-rate deductions if days != 30 (approximate)
        # However, for tax purposes, we usually look at the monthly equivalent
        pro_rate_factor = days / 30.0
        
        pro_rated_deductions = {
            "labor_insurance": round(monthly_insurance['labor_insurance'] * pro_rate_factor),
            "health_insurance": round(monthly_insurance['health_insurance'] * pro_rate_factor),
            "labor_pension": round(monthly_insurance['labor_pension'] * pro_rate_factor),
            "total_deductions": round(monthly_insurance['total_deductions'] * pro_rate_factor)
        }
        
        # Monthly equivalent for tax estimation
        monthly_equivalent = gross_salary / pro_rate_factor if pro_rate_factor > 0 else 0
        monthly_tax = self.estimate_income_tax(monthly_equivalent - monthly_insurance['total_deductions'])
        
        # Pro-rate the tax back to the period
        tax = round(monthly_tax * pro_rate_factor)
        
        net_salary = gross_salary - pro_rated_deductions['total_deductions'] - tax
        
        return {
            "gross": gross_salary,
            "deductions": pro_rated_deductions,
            "tax": tax,
            "net": net_salary,
            "is_pro_rated": days != 30,
            "days": days,
            "settings": {
                "insurance_salary": settings.insurance_salary,
                "dependents": settings.health_insurance_dependents,
                "pension_rate": settings.labor_pension_rate
            }
        }
