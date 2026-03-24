#!/usr/bin/env python3
"""
Quick test script to verify the registration endpoint works
"""

import json
import urllib.request
import urllib.error

API_URL = "http://localhost:8000/api"

def test_register():
    """Test user registration"""
    print("Testing registration endpoint...")
    
    payload = {
        "email": "test@example.com",
        "password": "password123",
        "username": "testuser"
    }
    
    try:
        req = urllib.request.Request(
            f"{API_URL}/auth/register",
            data=json.dumps(payload).encode('utf-8'),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            
            print(f"Status Code: {response.status}")
            print(f"Response: {json.dumps(data, indent=2)}")
            
            if response.status == 200:
                token = data.get("access_token")
                user_id = data.get("user_id")
                
                print(f"\n✅ Registration successful!")
                print(f"Token: {token[:20]}...")
                print(f"User ID: {user_id}")
                
                # Try to get user info
                print(f"\nTesting /auth/me endpoint...")
                me_req = urllib.request.Request(
                    f"{API_URL}/auth/me",
                    headers={"Authorization": f"Bearer {token}"}
                )
                
                with urllib.request.urlopen(me_req) as me_response:
                    me_data = json.loads(me_response.read().decode())
                    print(f"Me Status: {me_response.status}")
                    print(f"Me Response: {json.dumps(me_data, indent=2)}")
                
                return True
            
    except urllib.error.HTTPError as e:
        print(f"❌ HTTP Error {e.code}")
        try:
            error_data = json.loads(e.read().decode())
            print(f"Error Response: {json.dumps(error_data, indent=2)}")
        except:
            print(f"Error Response: {e.read().decode()}")
        return False
    except urllib.error.URLError as e:
        print(f"❌ Cannot connect to backend: {e}")
        print("Is it running on http://localhost:8000?")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_register()

