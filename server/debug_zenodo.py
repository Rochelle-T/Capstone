#!/usr/bin/env python3
"""Debug Zenodo API configuration"""
from app.config import settings

print("=== Zenodo Configuration ===")
print(f"API Token: {settings.ZENODO_API_TOKEN[:20]}..." if settings.ZENODO_API_TOKEN else "NOT SET")
print(f"Sandbox Mode: {settings.ZENODO_SANDBOX_MODE}")
print(f"Base URL: https://{'sandbox.' if settings.ZENODO_SANDBOX_MODE else ''}zenodo.org/api")

# Test the token by trying to list depositions
import requests

headers = {"Authorization": f"Bearer {settings.ZENODO_API_TOKEN}"}
base_url = "https://sandbox.zenodo.org/api" if settings.ZENODO_SANDBOX_MODE else "https://zenodo.org/api"

print("\n=== Testing Token ===")
test_url = f"{base_url}/deposit/depositions"
print(f"Testing: {test_url}")

try:
    resp = requests.get(test_url, headers=headers)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text[:200]}")
except Exception as e:
    print(f"Error: {e}")
