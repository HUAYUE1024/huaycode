import requests
import json

url = "http://127.0.0.1:5000/api/run"
payload = {
    "code": "print('hello')"
}
headers = {
    "Content-Type": "application/json"
}

try:
    response = requests.post(url, json=payload)
    print(f"Status: {response.status_code}")
    print(response.text)
except Exception as e:
    print(f"Request failed: {e}")
