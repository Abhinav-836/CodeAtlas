"""
CLI analyze command.
"""
import os
import sys

import requests

API_URL = os.getenv("CODEATLAS_API_URL", "http://127.0.0.1:8000")


def analyze_command(path: str) -> None:
    if not path:
        print("❌ Please provide --path")
        return
    if not os.path.exists(path):
        print("❌ Path does not exist")
        return

    url = f"{API_URL}/api/analyze"
    try:
        response = requests.post(
            url,
            params={"path": os.path.abspath(path)},
            timeout=30,
        )
        response.raise_for_status()
        print("✅ Analysis started successfully\n")
        print(response.json())
    except requests.exceptions.HTTPError as e:
        print(f"❌ Analysis failed ({response.status_code}): {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Analysis failed: {e}")
        print(f"   Make sure the API is running at {API_URL}")