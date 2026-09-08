import requests
import json
url = 'https://gnehs.github.io/ntut-course-crawler-node/api.json'
try:
    res = requests.get(url)
    print(res.text[:1000])
except Exception as e:
    print(e)
