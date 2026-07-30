from app import app
from models import db, User, UserSettings, VocabHistoryLog, VocabProgress
from datetime import datetime

with app.app_context():
    user = User.query.first()
    if not user:
        print("No user found")
        exit(1)
        
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user.id)
            
        # 1. Update settings
        res = client.post('/vocab/settings', data={'vocab_daily_goal': 35}, follow_redirects=True)
        print("Settings update status:", res.status_code)
        
        # 2. Check index for daily goal
        res = client.get('/vocab/')
        if b'35' in res.data:
            print("Daily goal 35 found on dashboard")
        else:
            print("Daily goal not found")
            
        # 3. Simulate vocab progress
        res = client.post('/vocab/api/progress', json={'word': 'history_test_word', 'result': 'correct'})
        print("Progress update status:", res.status_code)
        
        # 4. Check history log
        logs = VocabHistoryLog.query.filter_by(word='history_test_word').all()
        print(f"Found {len(logs)} history logs for 'history_test_word'")
        
        # 5. Check api_words review_date filter
        today_str = datetime.utcnow().strftime('%Y-%m-%d')
        res = client.get(f'/vocab/api/words?review_date={today_str}')
        data = res.get_json()
        print(f"API words with review_date {today_str} returned {data.get('total')} words")

        # Cleanup
        for log in logs:
            db.session.delete(log)
        vp = VocabProgress.query.filter_by(word='history_test_word').first()
        if vp:
            db.session.delete(vp)
        db.session.commit()
        print("Cleanup done")
