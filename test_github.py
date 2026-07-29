# test_github.py
from dotenv import load_dotenv
import os, httpx

load_dotenv()

token = os.getenv("GITHUB_TOKEN")
resp = httpx.get(
    "https://api.github.com/user",
    headers={"Authorization": f"Bearer {token}"}
)
print(f"Status: {resp.status_code}")
print(f"Logged in as: {resp.json().get('login')}")