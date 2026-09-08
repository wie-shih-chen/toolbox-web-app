import requests
import json
res = requests.get('https://gnehs.github.io/ntut-course-crawler-node/112/2/main.json')
data = res.json()
types = set()
for c in data:
    ctype = c.get('courseType')
    types.add(ctype)
print(types)
