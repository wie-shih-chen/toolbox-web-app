from app import create_app, db
from models import GroupDailyRecord, VocabHistoryLog, GroupDailyAssignment
from datetime import datetime, timedelta
import json

app = create_app()
with app.app_context():
    record = GroupDailyRecord.query.filter_by(group_id=1, user_id=1).order_by(GroupDailyRecord.id.desc()).first()
    if record:
        print("Record:", record.date, record.words_studied)
        logs = VocabHistoryLog.query.filter_by(source='group_1', user_id=1).all()
        # count only today's logs
        today_logs = [log for log in logs if log.created_at.strftime('%Y-%m-%d') == record.date]
        unique_words = {log.word for log in today_logs}
        print("Unique words studied today:", len(unique_words))
        
        assignment = GroupDailyAssignment.query.filter_by(group_id=1, date=record.date).first()
        if assignment:
            w_list = json.loads(assignment.words_json)
            assignment_words = {w['word'] for w in w_list}
            print("Assignment unique words:", len(assignment_words))
            print("Missing words:", assignment_words - unique_words)
            print("Issuperset:", unique_words.issuperset(assignment_words))
