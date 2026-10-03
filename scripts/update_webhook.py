import requests
import os
from dotenv import load_dotenv

current_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(os.path.dirname(current_dir), '.env'))

def get_ngrok_url():
    try:
        r = requests.get('http://127.0.0.1:4040/api/tunnels')
        data = r.json()
        for tunnel in data['tunnels']:
            if tunnel['public_url'].startswith('https'):
                return tunnel['public_url']
    except Exception as e:
        pass
    return None

def update_line_webhook(url):
    token = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    data = {
        "endpoint": f"{url}/webhook"
    }
    r = requests.put('https://api.line.me/v2/bot/channel/webhook/endpoint', headers=headers, json=data)
    print(f"Status Code: {r.status_code}")
    print(f"Response: {r.text}")

if __name__ == '__main__':
    url = get_ngrok_url()
    if url:
        print(f"Found ngrok URL: {url}")
        update_line_webhook(url)
    else:
        print("Could not find ngrok URL. Is ngrok running on port 4040?")
