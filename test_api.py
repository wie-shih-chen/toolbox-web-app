from app import app
from models import db, User, VocabProgress
import json

with app.app_context():
    user = User.query.first()
    
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user.id)
            
        res = client.post('/vocab/api/progress', json={
            'word': 'testword',
            'result': 'correct'
        })
        print(res.status_code, res.get_json())
        
        vp = VocabProgress.query.filter_by(word='testword').first()
        print("DB record correct:", vp.correct if vp else "None")

