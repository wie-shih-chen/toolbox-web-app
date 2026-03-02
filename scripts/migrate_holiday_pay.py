"""
migrate_holiday_pay.py — 補算所有歷史排班的國定假日薪資
Run on server: python scripts/migrate_holiday_pay.py

Finds every 'shift' record that falls on a Taiwan national holiday
and applies 2× pay (amount = hours × rate × 2) plus a note.
Runs in DRY-RUN mode by default; pass --apply to actually save.
"""
import sys, os, argparse

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(BASE_DIR, '.env'))

parser = argparse.ArgumentParser()
parser.add_argument('--apply', action='store_true', help='Actually write changes to DB (default: dry-run)')
args = parser.parse_args()

from app import app
from models import db, SalaryRecord
from services.tw_holidays import is_holiday

HOLIDAY_TAG = '【國定假日'

with app.app_context():
    shifts = SalaryRecord.query.filter_by(type='shift').all()
    print(f"Found {len(shifts)} shift records total.\n")

    updated = 0
    for r in shifts:
        holiday_name = is_holiday(r.date)
        if not holiday_name:
            continue

        # Skip if already tagged (were created after the feature was deployed)
        if r.note and HOLIDAY_TAG in r.note:
            print(f"  SKIP (already tagged): {r.date} {r.start_time}-{r.end_time}  note={r.note[:40]}")
            continue

        old_amount = r.amount
        new_amount = int(r.hours * r.rate * 2)
        note_prefix = f"【國定假日：{holiday_name}】工資加倍（{r.hours:.1f}h × {r.rate:.0f} × 2 = ${new_amount}）"
        new_note = note_prefix + (" " + (r.note or "")).strip()

        print(f"  {'[DRY]' if not args.apply else '[UPDATE]'} {r.date} {r.start_time}-{r.end_time} | "
              f"{r.hours}h × {r.rate:.0f} → ${old_amount}  =>  ×2 → ${new_amount}  ({holiday_name})")

        if args.apply:
            r.amount = new_amount
            r.note = new_note

        updated += 1

    if args.apply:
        db.session.commit()
        print(f"\n✅ Updated {updated} records.")
    else:
        print(f"\n🔍 Dry-run: {updated} records would be updated. Run with --apply to save.")
