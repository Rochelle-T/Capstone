#!/usr/bin/env python3
"""
Test Zenodo upload directly to see what error we're getting
"""
import os
import sys
import requests
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.config import settings

# Test configuration
ZENODO_TOKEN = settings.ZENODO_API_TOKEN
SANDBOX_MODE = settings.ZENODO_SANDBOX_MODE
ZENODO_BASE_URL = "https://sandbox.zenodo.org/api" if SANDBOX_MODE else "https://zenodo.org/api"

print(f"[CONFIG] Backend: {settings.STORAGE_BACKEND}")
print(f"[CONFIG] Zenodo Base URL: {ZENODO_BASE_URL}")
print(f"[CONFIG] Sandbox Mode: {SANDBOX_MODE}")
print(f"[CONFIG] Token: {ZENODO_TOKEN[:20]}..." if ZENODO_TOKEN else "[CONFIG] No token configured")

if not ZENODO_TOKEN:
    print("[ERROR] No Zenodo token configured in .env")
    sys.exit(1)

# Create test file
test_file_path = Path(__file__).parent / "test_zenodo.fits"
test_file_path.write_text("SIMPLE  =                    T / file does conform to FITS standard\nEND\n")
print(f"\n[TEST] Created test file: {test_file_path}")

# Step 1: Create deposition
print("\n[STEP 1] Creating deposition...")
headers = {"Authorization": f"Bearer {ZENODO_TOKEN}"}
metadata = {
    "metadata": {
        "title": "Test FITS Upload",
        "description": "Test upload from AstroSense debug script",
        "creators": [{"name": "Test User"}],
        "upload_type": "dataset",
        "keywords": ["test"]
    }
}

try:
    response = requests.post(
        f"{ZENODO_BASE_URL}/deposit/depositions",
        headers=headers,
        json=metadata
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text[:500]}")
    
    if response.status_code not in [201, 200]:
        print(f"[ERROR] Deposition creation failed!")
        sys.exit(1)
    
    deposition_id = response.json()["id"]
    print(f"[SUCCESS] Created deposition: {deposition_id}")
    
    # Step 2: Upload file
    print("\n[STEP 2] Uploading file...")
    with open(test_file_path, 'rb') as f:
        files = {'file': (test_file_path.name, f)}
        upload_response = requests.post(
            f"{ZENODO_BASE_URL}/deposit/depositions/{deposition_id}/files",
            headers=headers,
            files=files
        )
    
    print(f"Status: {upload_response.status_code}")
    print(f"Response: {upload_response.text[:500]}")
    
    if upload_response.status_code not in [201, 200]:
        print(f"[ERROR] File upload failed!")
        sys.exit(1)
    
    upload_json = upload_response.json()
    # Single file object (not array) - Zenodo returns direct file object
    file_id = upload_json.get("id")
    file_zenodo_url = upload_json.get("links", {}).get("self")
    print(f"[SUCCESS] Uploaded file: {file_id}")
    
    # Step 3: Publish
    print("\n[STEP 3] Publishing deposition...")
    publish_response = requests.post(
        f"{ZENODO_BASE_URL}/deposit/depositions/{deposition_id}/actions/publish",
        headers=headers
    )
    
    print(f"Status: {publish_response.status_code}")
    print(f"Response: {publish_response.text[:500]}")
    print(f"Response JSON: {publish_response.json()}")
    
    if publish_response.status_code not in [202, 201, 200]:
        print(f"[ERROR] Publish failed!")
        sys.exit(1)
    
    publish_json = publish_response.json()
    record_id = publish_json.get("record_id") or publish_json.get("id")
    print(f"[SUCCESS] Published! Record ID: {record_id}")
    
    if SANDBOX_MODE:
        url = f"https://sandbox.zenodo.org/record/{record_id}"
    else:
        url = f"https://zenodo.org/record/{record_id}"
    
    print(f"[SUCCESS] Access at: {url}")
    
except Exception as e:
    print(f"[EXCEPTION] {type(e).__name__}: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n[COMPLETE] All tests passed!")
