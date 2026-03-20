"""Quick test script for the /api/v1/run endpoint."""
import urllib.request
import json

url = "http://127.0.0.1:5000/api/v1/run"
payload = json.dumps({"code": "print('hello')"}).encode('utf-8')

req = urllib.request.Request(
    url,
    data=payload,
    headers={"Content-Type": "application/json"},
    method="POST"
)

try:
    with urllib.request.urlopen(req) as response:
        print(f"Status: {response.status}")
        print(response.read().decode('utf-8'))
except Exception as e:
    print(f"Request failed: {e}")
