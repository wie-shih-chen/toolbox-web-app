"""
migrate_holiday_pay.py — 補算所有歷史排班的國定假日薪資
Run: python scripts/migrate_holiday_pay.py           # dry-run (preview only)
     python scripts/migrate_holiday_pay.py --apply   # actually save

Uses ONLY Python built-ins (urllib, sqlite3) — no pip installs needed.
"""
import sys, os, sqlite3, argparse
import urllib.request

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── Find DB ──────────────────────────────────────────────────────────────────
db_path = None
env_file = os.path.join(BASE_DIR, '.env')
if os.path.exists(env_file):
    for line in open(env_file):
        line = line.strip()
        if line.startswith('DATABASE_URL') or line.startswith('SQLALCHEMY_DATABASE_URI'):
            val = line.split('=', 1)[1].strip().strip('"\'')
            if val.startswith('sqlite:///'):
                p = val[len('sqlite:///'):]
                db_path = p if os.path.isabs(p) else os.path.join(BASE_DIR, p)
            break

if not db_path:
    for name in ['app.db', 'database.db', 'toolbox.db', 'site.db']:
        candidate = os.path.join(BASE_DIR, name)
        if os.path.exists(candidate):
            db_path = candidate
            break

if not db_path:
    print("❌ Cannot find SQLite DB. Edit db_path manually.")
    sys.exit(1)

print(f"📂 DB: {db_path}\n")

# ── LSA whitelist ─────────────────────────────────────────────────────────────
_LSA_KEYWORDS = [
    "開國紀念", "元旦", "小年夜", "除夕", "春節", "初一", "初二", "初三",
    "和平紀念", "兒童節", "清明", "掃墓", "勞動節", "端午", "中秋",
    "教師節", "孔子", "國慶", "臺灣光復", "台灣光復", "光復節", "古寧頭",
    "行憲紀念",
]

def _is_lsa(name):
    return any(kw in name for kw in _LSA_KEYWORDS)

# ── Parse ICS without external libs ──────────────────────────────────────────
TW_ICS_URL = (
    "https://calendar.google.com/calendar/ical/"
    "zh-tw.taiwan%23holiday%40group.v.calendar.google.com/public/basic.ics"
)

def fetch_holidays():
    """Returns {YYYY-MM-DD: holiday_name} using only built-in urllib."""
    print("📡 Fetching Taiwan holidays from Google Calendar...")
    try:
        req = urllib.request.Request(TW_ICS_URL, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode('utf-8', errors='replace')
    except Exception as e:
        print(f"❌ Cannot fetch ICS: {e}")
        sys.exit(1)

    result = {}
    cur_date = None
    cur_name = None
    in_event = False

    for line in raw.splitlines():
        line = line.strip()
        if line == 'BEGIN:VEVENT':
            in_event = True
            cur_date = None
            cur_name = None
        elif line == 'END:VEVENT':
            if in_event and cur_date and cur_name and _is_lsa(cur_name):
                result[cur_date] = cur_name
            in_event = False
        elif in_event:
            if line.startswith('DTSTART'):
                # DTSTART;VALUE=DATE:20260228  OR  DTSTART:20260228
                val = line.split(':', 1)[-1].strip()
                if len(val) == 8 and val.isdigit():
                    cur_date = f"{val[:4]}-{val[4:6]}-{val[6:8]}"
            elif line.startswith('SUMMARY:'):
                name = line[len('SUMMARY:'):]
                # Strip Google's " (substitute)" suffix
                cur_name = name.split(' (')[0].strip()

    print(f"✅ Loaded {len(result)} LSA national holidays.\n")
    return result

# ── Main ─────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument('--apply', action='store_true', help='Write changes (default: dry-run)')
args = parser.parse_args()

holidays = fetch_holidays()

HOLIDAY_TAG = '【國定假日'

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

rows = cur.execute(
    "SELECT id, date, start_time, end_time, hours, rate, amount, note FROM salary_record WHERE type='shift'"
).fetchall()
print(f"Found {len(rows)} shift records.\n")

updates = []
for r in rows:
    holiday_name = holidays.get(r['date'])
    if not holiday_name:
        continue

    note = r['note'] or ''
    if HOLIDAY_TAG in note:
        print(f"  SKIP (already tagged): {r['date']}  {r['start_time']}-{r['end_time']}")
        continue

    hours = r['hours'] or 0
    rate  = r['rate']  or 0
    old_amount = r['amount'] or 0
    new_amount = int(hours * rate * 2)
    note_prefix = f"【國定假日：{holiday_name}】工資加倍（{hours:.1f}h × {rate:.0f} × 2 = ${new_amount}）"
    new_note = note_prefix + (" " + note).strip()

    tag = '[DRY]' if not args.apply else '[UPDATE]'
    print(f"  {tag} {r['date']} {r['start_time']}-{r['end_time']} | "
          f"{hours}h × {rate:.0f} = ${old_amount}  →  ×2 = ${new_amount}  ({holiday_name})")
    updates.append((new_amount, new_note, r['id']))

if args.apply and updates:
    cur.executemany("UPDATE salary_record SET amount=?, note=? WHERE id=?", updates)
    conn.commit()
    print(f"\n✅ Updated {len(updates)} records.")
elif updates:
    print(f"\n🔍 Dry-run: {len(updates)} records would be updated. Run with --apply to save.")
else:
    print("\n✅ No records need updating.")

conn.close()
