import requests

BASE_URL = "http://192.168.29.217:5000"
key = ""
payload = {
    "username": "admin",
    "password": "password",
    "api_key": key,
    "command": ""
}
res = requests.post(f"{BASE_URL}/execute", json=payload)
print(f"API Response: {res.json()}")
assert res.status_code == 200   