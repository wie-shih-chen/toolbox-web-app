"""
Migration Script: Migrate existing UserSettings.line_user_id → LineBinding table.
Run once after deploying the new LineBinding model.
Usage (PythonAnywhere Bash):
  cd /path/to/web_app && python scripts/maintenance/migrate_line_bindings.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from models import UserSettings, LineBinding

app = create_app()
with app.app_context():
    db.create_all()  # Creates LineBinding table if not exists

    migrated = 0
    skipped = 0
    settings_list = UserSettings.query.filter(UserSettings.line_user_id.isnot(None)).all()

    for s in settings_list:
        existing = LineBinding.query.filter_by(line_user_id=s.line_user_id).first()
        if existing:
            print(f"  [SKIP] user_id={s.user_id} — LINE ID already in LineBinding")
            skipped += 1
            continue

        binding = LineBinding(
            user_id=s.user_id,
            line_user_id=s.line_user_id,
            nickname='本人',
            permissions='["expense","salary","period"]'
        )
        db.session.add(binding)
        migrated += 1
        print(f"  [MIGRATED] user_id={s.user_id} → LineBinding created")

    db.session.commit()
    print(f"\n✅ Done. Migrated: {migrated}, Skipped: {skipped}")
