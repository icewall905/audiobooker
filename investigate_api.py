#!/usr/bin/env python3
"""
Investigate alternative result retrieval methods.
"""

import requests
import json
import time

SERVER_URL = "http://10.0.10.23:7860"

def investigate_response_pattern():
    """Try to understand how this specific Gradio setup handles results."""
    
    print("=== Making API Call and Monitoring ===")
    api_endpoint = f"{SERVER_URL}/gradio_api/call/generate"
    
    data = {
        "data": [
            None,  # State object
            "Short test",  # Very short text for quick processing
            None,  # Voice prompt file
            0.5,   # Exaggeration parameter
            0.8,   # Temperature parameter
            0,     # Random seed
            0.5    # CFG weight parameter
        ],
        "event_data": None,
        "fn_index": 1,  # Use correct fn_index from config
        "trigger_id": None
    }
    
    print(f"Sending request...")
    response = requests.post(api_endpoint, json=data, timeout=30)
    result = response.json()
    event_id = result['event_id']
    
    print(f"Got event_id: {event_id}")
    
    # Since standard endpoints don't work, let's try some creative approaches
    print(f"\n=== Trying Alternative Approaches ===")
    
    # Maybe it's using WebSocket URLs
    ws_endpoints = [
        f"/ws",
        f"/websocket", 
        f"/ws/{event_id}",
        f"/websocket/{event_id}"
    ]
    
    for endpoint in ws_endpoints:
        try:
            url = f"{SERVER_URL}{endpoint}"
            test_response = requests.get(url, timeout=5)
            print(f"  {endpoint}: Status {test_response.status_code}")
        except Exception as e:
            print(f"  {endpoint}: Error - {e}")
    
    # Maybe there's a different API endpoint pattern
    alt_endpoints = [
        f"/api",
        f"/api/generate",
        f"/api/generate/{event_id}",
        f"/api/status",
        f"/api/status/{event_id}",
        f"/generate",
        f"/generate/{event_id}",
        f"/output/{event_id}",
        f"/download/{event_id}",
        f"/temp/{event_id}"
    ]
    
    print(f"\n=== Trying Alternative API Endpoints ===")
    for endpoint in alt_endpoints:
        try:
            url = f"{SERVER_URL}{endpoint}"
            test_response = requests.get(url, timeout=5)
            print(f"  {endpoint}: Status {test_response.status_code}")
            
            if test_response.status_code == 200:
                content_type = test_response.headers.get('content-type', '')
                content_length = len(test_response.content)
                print(f"    Content-Type: {content_type}, Length: {content_length}")
                
                if content_length < 500:
                    try:
                        data = test_response.json()
                        print(f"    JSON: {json.dumps(data, indent=2)}")
                    except:
                        print(f"    Text: {test_response.text}")
        except Exception as e:
            print(f"  {endpoint}: Error - {e}")
    
    # Wait a bit and try the same event_id again
    print(f"\n=== Waiting 10 seconds then retrying event_id ===")
    time.sleep(10)
    
    retry_endpoints = [
        f"/gradio_api/call/generate/{event_id}",
        f"/gradio_api/{event_id}",
        f"/gradio_api/result/{event_id}",
        f"/gradio_api/status/{event_id}"
    ]
    
    for endpoint in retry_endpoints:
        try:
            url = f"{SERVER_URL}{endpoint}"
            test_response = requests.get(url, timeout=5)
            print(f"  {endpoint}: Status {test_response.status_code}")
            
            if test_response.status_code == 200:
                content_type = test_response.headers.get('content-type', '')
                content_length = len(test_response.content)
                print(f"    Content-Type: {content_type}, Length: {content_length}")
                
                if 'audio' in content_type or content_length > 1000:
                    print(f"    🎉 Found audio! Saving as test_audio_{event_id}.wav")
                    with open(f"test_audio_{event_id}.wav", "wb") as f:
                        f.write(test_response.content)
                elif content_length < 500:
                    try:
                        data = test_response.json()
                        print(f"    JSON: {json.dumps(data, indent=2)}")
                    except:
                        print(f"    Text: {test_response.text}")
        except Exception as e:
            print(f"  {endpoint}: Error - {e}")

if __name__ == "__main__":
    investigate_response_pattern()
