import os
import requests

API_URL = "http://127.0.0.1:8000/analyze"

def analyze_command(path: str):
    if not path:
        print("❌ Please provide --path")
        return

    if not os.path.exists(path):
        print("❌ Path does not exist")
        return

    payload = {
        "path": os.path.abspath(path)
    }

    try:
        response = requests.post(API_URL, json=payload)
        response.raise_for_status()
        print("✅ Analysis completed successfully\n")
        print(response.json())
    except requests.exceptions.RequestException as e:
        print("❌ Analysis failed:", str(e))
