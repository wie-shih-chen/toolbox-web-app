import requests
import sqlite3

# Try inserting manually into the db to see if it works
conn = sqlite3.connect('app.db')
c = conn.cursor()
c.execute("INSERT INTO vocab_progress (user_id, word, correct, incorrect, last_reviewed) VALUES (1, 'test', 1, 0, '2026-07-27 00:00:00');")
conn.commit()
conn.close()
print("inserted manually")
