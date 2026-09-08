import requests
res = requests.get('https://gnehs.github.io/ntut-course-crawler-node/112/2/main.json')
data = res.json()
print("Sample class array:")
print(data[0]['class'])
