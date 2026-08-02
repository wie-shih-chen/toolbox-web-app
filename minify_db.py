import sys
import os
import json

# Setup Flask app context
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app import app
from models import db, GroupDailyAssignment

def minify_assignments():
    with app.app_context():
        assignments = GroupDailyAssignment.query.all()
        count = 0
        for assignment in assignments:
            if not assignment.words_json:
                continue
            raw_list = json.loads(assignment.words_json)
            if not raw_list:
                continue
                
            # If the first item is a dict, it's the old bloated format
            if isinstance(raw_list[0], dict):
                # Extract only the word strings
                word_strings = [w['word'] for w in raw_list if 'word' in w]
                # Update the database
                assignment.words_json = json.dumps(word_strings, ensure_ascii=False)
                count += 1
                print(f"Minified group {assignment.group_id} assignment for {assignment.date}")
                
        if count > 0:
            db.session.commit()
            print(f"Successfully minified {count} assignments!")
        else:
            print("No assignments needed minification. All good!")

if __name__ == '__main__':
    minify_assignments()
