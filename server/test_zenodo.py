#!/usr/bin/env python3
"""Test Zenodo integration"""
import requests
import time
import json

time.sleep(3)  # Give backend time to start

print('[TEST] Attempting Zenodo upload...')

# Create a minimal FITS file for testing
fits_content = b'SIMPLE  =                    T / file does comply with FITS standard'
fits_content += b' ' * (2880 - len(fits_content))

# Try to register first
register_data = {
    'email': 'zenodo_test3@test.com',
    'password': 'test12345',
    'username': 'zentest3'
}

try:
    reg_resp = requests.post('http://localhost:8000/api/auth/register', json=register_data)
    print(f'Register: {reg_resp.status_code}')
    
    if reg_resp.status_code == 200:
        token = reg_resp.json()['access_token']
        print(f'Token obtained: {token[:20]}...')
        
        # Try file upload
        files = {'file': ('test_zenodo.fits', fits_content)}
        headers = {'Authorization': f'Bearer {token}'}
        
        print('Uploading to Zenodo...')
        upload_resp = requests.post('http://localhost:8000/api/upload/fits', headers=headers, files=files)
        print(f'Upload response: {upload_resp.status_code}')
        
        if upload_resp.status_code == 200:
            resp_json = upload_resp.json()
            print(json.dumps(resp_json, indent=2))
            print(f"\nBackend: {resp_json.get('backend', 'unknown')}")
            print(f"Public URL: {resp_json.get('public_url', 'N/A')}")
            print(f"Zenodo Record ID: {resp_json.get('zenodo_record_id', 'N/A')}")
        else:
            print(f'Upload error: {upload_resp.text}')
    else:
        print(f'Register error: {reg_resp.text}')

except Exception as e:
    print(f'Error: {type(e).__name__}: {e}')
    import traceback
    traceback.print_exc()
